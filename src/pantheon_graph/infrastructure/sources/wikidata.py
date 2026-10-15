import re
from typing import Any

import httpx2 as httpx

from pantheon_graph.config import WikidataSettings
from pantheon_graph.domain import Edge, Graph, Node, NodeKind, Relation
from pantheon_graph.infrastructure.sources._common import relation_edge

GREEK_DEITY = 'Q22989102'
ZEUS = 'Q34201'
GENDERS = {'Q6581097': ('male', NodeKind.GOD), 'Q6581072': ('female', NodeKind.GODDESS)}

# Wikidata property -> (relation, label, whether the statement points child -> parent)
PROPERTIES: dict[str, tuple[Relation, str, bool]] = {
    'P22': (Relation.PARENT, 'father', True),
    'P25': (Relation.PARENT, 'mother', True),
    'P26': (Relation.SPOUSE, 'spouse', False),
    'P3373': (Relation.SIBLING, 'sibling', False),
}

_QID = re.compile(r'/(Q\d+)$')
_PID = re.compile(r'/(P\d+)$')


class WikidataSource:
    """Greek deities and their family ties from the Wikidata SPARQL endpoint."""

    name = 'wikidata'

    def __init__(self, client: httpx.AsyncClient, settings: WikidataSettings) -> None:
        self._client = client
        self._settings = settings

    async def fetch(self) -> Graph:
        nodes = await self._fetch_nodes()
        edges = await self._fetch_edges(list(nodes))
        return Graph.build(nodes.values(), edges)

    async def ping(self) -> bool:
        data = await self._query(f'ASK {{ wd:{ZEUS} ?p ?o }}')
        return bool(data.get('boolean'))

    async def _fetch_nodes(self) -> dict[str, Node]:
        rows = await self._select(f"""
            SELECT ?item ?itemLabel ?itemDescription ?gender WHERE {{
              ?item wdt:P31/wdt:P279* wd:{GREEK_DEITY} .
              OPTIONAL {{ ?item wdt:P21 ?gender . }}
              SERVICE wikibase:label {{
                bd:serviceParam wikibase:language "{self._settings.language},en" .
              }}
            }}
            LIMIT {self._settings.node_limit}
        """)
        nodes: dict[str, Node] = {}
        for row in rows:
            qid = _match(_QID, row.get('item'))
            label = row.get('itemLabel')
            # Items without a label in the requested languages come back labelled by their QID
            if not qid or not label or label == qid or qid in nodes:
                continue
            properties = {'source': self.name, 'url': f'https://www.wikidata.org/wiki/{qid}'}
            if description := row.get('itemDescription'):
                properties['description'] = description
            kind = NodeKind.DEITY
            if gender := GENDERS.get(_match(_QID, row.get('gender')) or ''):
                properties['gender'], kind = gender
            nodes[qid] = Node(id=qid, label=label, kind=kind, properties=properties)
        return nodes

    async def _fetch_edges(self, qids: list[str]) -> list[Edge]:
        if not qids:
            return []
        entities = ' '.join(f'wd:{qid}' for qid in qids)
        properties = ' '.join(f'wdt:{pid}' for pid in PROPERTIES)
        rows = await self._select(f"""
            SELECT ?source ?property ?target WHERE {{
              VALUES ?source {{ {entities} }}
              VALUES ?target {{ {entities} }}
              VALUES ?property {{ {properties} }}
              ?source ?property ?target .
            }}
            LIMIT {self._settings.edge_limit}
        """)
        edges: dict[str, Edge] = {}
        for row in rows:
            source = _match(_QID, row.get('source'))
            target = _match(_QID, row.get('target'))
            pid = _match(_PID, row.get('property'))
            if not (source and target and pid in PROPERTIES) or source == target:
                continue
            relation, label, reversed_ = PROPERTIES[pid]
            if reversed_:
                source, target = target, source
            edge = relation_edge(source, target, relation, label=label, source=self.name)
            edges.setdefault(edge.id, edge)
        return list(edges.values())

    async def _select(self, query: str) -> list[dict[str, str]]:
        data = await self._query(query)
        return [
            {name: cell['value'] for name, cell in binding.items()}
            for binding in data.get('results', {}).get('bindings', [])
        ]

    async def _query(self, query: str) -> dict[str, Any]:
        # POST keeps the long VALUES lists clear of URL length limits
        response = await self._client.post(
            self._settings.endpoint,
            data={'query': query},
            headers={'Accept': 'application/sparql-results+json'},
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result


def _match(pattern: re.Pattern[str], uri: str | None) -> str | None:
    if uri and (match := pattern.search(uri)):
        return match.group(1)
    return None
