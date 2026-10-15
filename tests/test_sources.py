from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import parse_qs

import httpx2 as httpx
import pytest

from pantheon_graph.config import ArangoSettings, Neo4jSettings, WikidataSettings
from pantheon_graph.domain import Relation
from pantheon_graph.infrastructure.sources.arango import ArangoSource
from pantheon_graph.infrastructure.sources.memory import MemorySource
from pantheon_graph.infrastructure.sources.neo4j import Neo4jSource
from pantheon_graph.infrastructure.sources.wikidata import WikidataSource

pytestmark = pytest.mark.anyio


async def test_bundled_dataset_is_consistent() -> None:
    graph = await MemorySource.bundled().fetch()

    assert graph.without_dangling_edges() is graph, 'edges must reference known nodes'
    assert len({node.id for node in graph.nodes}) == len(graph.nodes)
    assert {edge.kind for edge in graph.edges} <= set(Relation)
    parents = {edge.source for edge in graph.edges if edge.target == 'athena'}
    assert parents == {'zeus', 'metis'}


# --- Wikidata -------------------------------------------------------------------------

ENTITY = 'http://www.wikidata.org/entity/'
PROP = 'http://www.wikidata.org/prop/direct/'


def cell(value: str) -> dict[str, str]:
    return {'type': 'uri', 'value': value}


NODE_ROWS = [
    {
        'item': cell(ENTITY + 'Q34201'),
        'itemLabel': cell('Zeus'),
        'itemDescription': cell('king of the gods'),
        'gender': cell(ENTITY + 'Q6581097'),
    },
    {'item': cell(ENTITY + 'Q34201'), 'itemLabel': cell('Zeus')},  # duplicate row
    {
        'item': cell(ENTITY + 'Q35500'),
        'itemLabel': cell('Hera'),
        'gender': cell(ENTITY + 'Q6581072'),
    },
    {'item': cell(ENTITY + 'Q40901'), 'itemLabel': cell('Ares')},
    {'item': cell(ENTITY + 'Q999'), 'itemLabel': cell('Q999')},  # unlabelled
]

EDGE_ROWS = [
    {
        'source': cell(ENTITY + 'Q34201'),
        'property': cell(PROP + 'P26'),
        'target': cell(ENTITY + 'Q35500'),
    },
    {
        'source': cell(ENTITY + 'Q35500'),
        'property': cell(PROP + 'P26'),
        'target': cell(ENTITY + 'Q34201'),
    },
    {
        'source': cell(ENTITY + 'Q40901'),
        'property': cell(PROP + 'P22'),
        'target': cell(ENTITY + 'Q34201'),
    },
]


def wikidata(handler: Any) -> WikidataSource:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return WikidataSource(client, WikidataSettings(endpoint='https://sparql.test/'))


def sparql_handler(request: httpx.Request) -> httpx.Response:
    query = parse_qs(request.content.decode())['query'][0]
    if query.startswith('ASK'):
        return httpx.Response(200, json={'boolean': True})
    rows = NODE_ROWS if 'itemLabel' in query else EDGE_ROWS
    return httpx.Response(200, json={'results': {'bindings': rows}})


async def test_wikidata_normalizes_nodes_and_edges() -> None:
    graph = await wikidata(sparql_handler).fetch()

    kinds = {node.id: node.kind for node in graph.nodes}
    assert kinds == {'Q34201': 'god', 'Q35500': 'goddess', 'Q40901': 'deity'}
    assert graph.node('Q34201').properties['description'] == 'king of the gods'
    # the symmetric spouse statement collapses to one edge, "child P22 father" is flipped
    assert {(e.source, e.target, e.kind, e.label) for e in graph.edges} == {
        ('Q34201', 'Q35500', 'spouse', 'spouse'),
        ('Q34201', 'Q40901', 'parent', 'father'),
    }


async def test_wikidata_ping() -> None:
    assert await wikidata(sparql_handler).ping() is True


async def test_wikidata_http_errors_propagate() -> None:
    source = wikidata(lambda _: httpx.Response(503))

    with pytest.raises(httpx.HTTPStatusError):
        await source.fetch()


# --- Neo4j ----------------------------------------------------------------------------


class FakeRecord(dict[str, Any]):
    def data(self) -> dict[str, Any]:
        return dict(self)


class FakeNeo4jDriver:
    async def execute_query(self, query: str, parameters: dict[str, Any], **_: Any) -> Any:
        if 'MATCH (n)' in query:
            rows = [
                FakeRecord(
                    id='4:a',
                    key='zeus',
                    label='Zeus',
                    kind='god',
                    props={'id': 'zeus', 'roman': 'Jupiter'},
                ),
                FakeRecord(
                    id='4:b', key='4:b', label='Hera', kind='goddess', props={'name': 'Hera'}
                ),
            ]
        else:
            rows = [
                FakeRecord(
                    id='5:r', source='4:a', target='4:b', kind='spouse', label='spouse', props={}
                ),
            ]
        return rows, None, None

    async def verify_connectivity(self) -> None:
        return None


async def test_neo4j_maps_element_ids_to_node_keys() -> None:
    source = Neo4jSource(FakeNeo4jDriver(), Neo4jSettings())  # type: ignore[arg-type]

    graph = await source.fetch()

    assert [node.id for node in graph.nodes] == ['zeus', '4:b']
    assert dict(graph.node('zeus').properties) == {'roman': 'Jupiter', 'source': 'neo4j'}
    assert (graph.edges[0].source, graph.edges[0].target) == ('zeus', '4:b')
    assert await source.ping()


# --- ArangoDB -------------------------------------------------------------------------

ARANGO_DOCS: dict[str, list[dict[str, Any]]] = {
    'deities': [
        {'_id': 'deities/zeus', '_key': 'zeus', '_rev': '1', 'name': 'Zeus', 'kind': 'god'},
        {'_id': 'deities/hera', '_key': 'hera', '_rev': '1', 'name': 'Hera'},
    ],
    'relations': [
        {
            '_id': 'relations/x',
            '_key': 'zeus-hera-spouse',
            '_from': 'deities/zeus',
            '_to': 'deities/hera',
            'kind': 'spouse',
        },
    ],
}


class FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = docs

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        for doc in self._docs:
            yield doc


class FakeArangoGraph:
    async def edge_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                'edge_collection': 'relations',
                'from_vertex_collections': ['deities'],
                'to_vertex_collections': ['deities'],
            }
        ]


class FakeArangoDb:
    def __init__(self) -> None:
        self.aql = self
        self.bind_vars: list[dict[str, Any]] = []

    async def execute(self, query: str, bind_vars: dict[str, Any]) -> FakeCursor:
        self.bind_vars.append(bind_vars)
        return FakeCursor(ARANGO_DOCS[bind_vars['@collection']])

    def graph(self, name: str) -> 'FakeArangoGraph':
        return FakeArangoGraph()

    async def version(self) -> str:
        return '3.12'


async def test_arango_reads_named_graph_with_bind_parameters() -> None:
    db = FakeArangoDb()

    graph = await ArangoSource(db, ArangoSettings(graph='pantheon')).fetch()

    assert [node.id for node in graph.nodes] == ['zeus', 'hera']
    assert graph.node('hera').kind == 'deities'  # falls back to the collection name
    edge = graph.edges[0]
    assert (edge.id, edge.source, edge.target, edge.kind) == (
        'zeus-hera-spouse',
        'zeus',
        'hera',
        'spouse',
    )
    assert '_rev' not in graph.node('zeus').properties
    assert {'@collection': 'deities', 'limit': 1000} in db.bind_vars
