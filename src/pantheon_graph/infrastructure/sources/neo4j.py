from typing import Any, LiteralString

from neo4j import AsyncDriver, RoutingControl

from pantheon_graph.config import Neo4jSettings
from pantheon_graph.domain import Edge, Graph, Node
from pantheon_graph.infrastructure.sources._common import clean_properties

NODES_QUERY: LiteralString = """
MATCH (n)
RETURN elementId(n) AS id,
       coalesce(n.id, elementId(n)) AS key,
       coalesce(n.name, n.label, n.title, labels(n)[0]) AS label,
       coalesce(n.kind, toLower(labels(n)[0])) AS kind,
       properties(n) AS props
LIMIT $limit
"""

EDGES_QUERY: LiteralString = """
MATCH (a)-[r]->(b)
RETURN coalesce(r.id, elementId(r)) AS id,
       elementId(a) AS source,
       elementId(b) AS target,
       coalesce(r.kind, toLower(type(r))) AS kind,
       coalesce(r.label, toLower(type(r))) AS label,
       properties(r) AS props
LIMIT $limit
"""

_RESERVED = frozenset({'id', 'name', 'label', 'kind'})


class Neo4jSource:
    """Read-only snapshot of a Neo4j database.

    Nodes keep their own ``id`` property when present, so the graph seeded
    from the bundled dataset merges cleanly with the other sources.
    """

    name = 'neo4j'

    def __init__(self, driver: AsyncDriver, settings: Neo4jSettings) -> None:
        self._driver = driver
        self._settings = settings

    async def fetch(self) -> Graph:
        node_rows = await self._read(NODES_QUERY, limit=self._settings.node_limit)
        edge_rows = await self._read(EDGES_QUERY, limit=self._settings.edge_limit)

        keys = {row['id']: str(row['key']) for row in node_rows}
        nodes = [
            Node(
                id=keys[row['id']],
                label=str(row['label']),
                kind=row['kind'],
                properties=clean_properties(row['props'], skip=_RESERVED) | {'source': self.name},
            )
            for row in node_rows
        ]
        edges = [
            Edge(
                id=str(row['id']),
                source=keys.get(row['source'], row['source']),
                target=keys.get(row['target'], row['target']),
                kind=row['kind'],
                label=row['label'],
                properties=clean_properties(row['props'], skip=_RESERVED) | {'source': self.name},
            )
            for row in edge_rows
        ]
        return Graph.build(nodes, edges)

    async def ping(self) -> bool:
        await self._driver.verify_connectivity()
        return True

    async def _read(self, query: LiteralString, **parameters: Any) -> list[dict[str, Any]]:
        records, _, _ = await self._driver.execute_query(
            query,
            parameters,
            routing_=RoutingControl.READ,
            database_=self._settings.database,
        )
        return [record.data() for record in records]
