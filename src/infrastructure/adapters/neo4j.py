from neo4j import AsyncGraphDatabase  # type: ignore[import-untyped]

from application.services import GraphAdapter
from core.config import Neo4jConfig
from domain.models import Edge, Graph, Node


class Neo4jAdapter(GraphAdapter):
    """Neo4j read-only adapter to fetch a generic graph snapshot."""

    def __init__(self, cfg: Neo4jConfig):
        self._driver = AsyncGraphDatabase.driver(cfg.uri, auth=(cfg.user, cfg.password))

    async def get_graph(self) -> Graph:
        nodes: list[Node] = []
        edges: list[Edge] = []
        async with self._driver.session() as session:  # type: ignore
            node_result = await session.run(
                """
                MATCH (n)
                RETURN toString(id(n)) AS id,
                       coalesce(n.name, labels(n)[0]) AS label,
                       labels(n)[0] AS type,
                       properties(n) AS props
                LIMIT 2000
                """
            )
            async for rec in node_result:  # type: ignore
                nodes.append(
                    Node(
                        id=rec["id"],
                        label=rec["label"],
                        type=rec["type"],
                        props=dict(rec["props"] or {}),
                    )
                )

            edge_result = await session.run(
                """
                MATCH (a)-[r]->(b)
                RETURN toString(id(r)) AS id,
                       toString(id(a)) AS source,
                       toString(id(b)) AS target,
                       type(r) AS type,
                       type(r) AS label,
                       properties(r) AS props
                LIMIT 4000
                """
            )
            async for rec in edge_result:  # type: ignore
                edges.append(
                    Edge(
                        id=rec["id"],
                        source=rec["source"],
                        target=rec["target"],
                        type=rec["type"],
                        label=rec["label"],
                        props=dict(rec["props"] or {}),
                    )
                )
        return Graph(nodes=nodes, edges=edges)
