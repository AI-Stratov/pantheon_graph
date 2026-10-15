from typing import Any

from arangoasync.database import StandardDatabase

from pantheon_graph.config import ArangoSettings
from pantheon_graph.domain import Edge, Graph, Node
from pantheon_graph.infrastructure.sources._common import clean_properties

# Collection names are bind parameters (@@collection), never interpolated into AQL
COLLECTION_QUERY = 'FOR doc IN @@collection LIMIT @limit RETURN doc'

_RESERVED = frozenset({'name', 'label', 'title', 'kind'})


class ArangoSource:
    """Snapshot of an ArangoDB named graph or an explicit vertex/edge collection pair.

    Vertices are identified by their ``_key`` so that data seeded from the
    bundled dataset lines up with the other sources.
    """

    name = 'arango'

    def __init__(self, database: StandardDatabase, settings: ArangoSettings) -> None:
        self._db = database
        self._settings = settings

    async def fetch(self) -> Graph:
        vertex_collections, edge_collections = await self._collections()
        nodes = [
            self._to_node(document)
            for collection in vertex_collections
            for document in await self._documents(collection, self._settings.node_limit)
        ]
        edges = [
            self._to_edge(document, collection)
            for collection in edge_collections
            for document in await self._documents(collection, self._settings.edge_limit)
        ]
        return Graph.build(nodes, edges)

    async def ping(self) -> bool:
        await self._db.version()
        return True

    async def _collections(self) -> tuple[list[str], list[str]]:
        settings = self._settings
        if settings.vertex_collection and settings.edge_collection:
            return [settings.vertex_collection], [settings.edge_collection]

        assert settings.graph, 'validated by ArangoSettings'
        definitions: list[dict[str, Any]] = await self._db.graph(settings.graph).edge_definitions()
        vertices = {
            name
            for definition in definitions
            for name in (
                *definition['from_vertex_collections'],
                *definition['to_vertex_collections'],
            )
        }
        return sorted(vertices), [definition['edge_collection'] for definition in definitions]

    async def _documents(self, collection: str, limit: int) -> list[dict[str, Any]]:
        cursor = await self._db.aql.execute(
            COLLECTION_QUERY, bind_vars={'@collection': collection, 'limit': limit}
        )
        assert cursor is not None
        documents: list[dict[str, Any]] = [document async for document in cursor]
        return documents

    def _to_node(self, document: dict[str, Any]) -> Node:
        return Node(
            id=_key(document['_id']),
            label=str(document.get('name') or document.get('label') or document['_key']),
            kind=document.get('kind') or document['_id'].partition('/')[0],
            properties=clean_properties(document, skip=_RESERVED) | {'source': self.name},
        )

    def _to_edge(self, document: dict[str, Any], collection: str) -> Edge:
        kind = str(document.get('kind') or collection)
        return Edge(
            id=document['_key'],
            source=_key(document['_from']),
            target=_key(document['_to']),
            kind=kind,
            label=str(document.get('label') or kind),
            properties=clean_properties(document, skip=_RESERVED) | {'source': self.name},
        )


def _key(document_id: str) -> str:
    """``deities/zeus`` -> ``zeus``."""
    return document_id.rpartition('/')[2]
