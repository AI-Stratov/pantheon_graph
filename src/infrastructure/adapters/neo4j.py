from typing import final, Any

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from application.services import GraphAdapterInterface
from core.config import Neo4jConfig
from core.constants import DatabaseLimits
from domain.models import Edge, Graph, Node


@final
class Neo4jAdapter(GraphAdapterInterface):  # type: ignore[misc]
    """Neo4j database adapter for graph data retrieval.

    This adapter connects to a Neo4j database and fetches graph data
    using Cypher queries. It provides read-only access to the graph.

    Attributes:
        _driver: Neo4j async driver for database connections
        _node_limit: Maximum number of nodes to fetch
        _edge_limit: Maximum number of edges to fetch
    """

    def __init__(self, config: Neo4jConfig) -> None:
        """Initialize Neo4j adapter with configuration.

        Args:
            config: Neo4j connection configuration
        """
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            config.uri,
            auth=(config.user, config.password)
        )
        self._node_limit = DatabaseLimits.NEO4J_NODE_LIMIT
        self._edge_limit = DatabaseLimits.NEO4J_EDGE_LIMIT

    async def get_graph(self) -> Graph:
        """Retrieve graph data from Neo4j database.

        Returns:
            Graph object containing nodes and edges from the database

        Raises:
            Exception: If database connection or query fails
        """
        nodes: list[Node] = []
        edges: list[Edge] = []

        async with self._driver.session() as session:
            nodes = await self._fetch_nodes(session)
            edges = await self._fetch_edges(session)

        return Graph(nodes=nodes, edges=edges)

    async def health_check(self) -> bool:
        """Check if Neo4j database is accessible and responsive.

        Returns:
            True if database is accessible, False otherwise
        """
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                return record is not None and record["test"] == 1
        except Exception:
            return False

    async def _fetch_nodes(self, session: AsyncSession) -> list[Node]:
        """Fetch nodes from Neo4j database.

        Args:
            session: Active Neo4j session

        Returns:
            List of Node objects from the database
        """
        query = """
        MATCH (n)
        RETURN toString(id(n)) AS id,
               coalesce(n.name, labels(n)[0]) AS label,
               labels(n)[0] AS type,
               properties(n) AS props
        LIMIT $limit
        """

        result = await session.run(query, limit=self._node_limit)
        nodes: list[Node] = []

        async for record in result:
            nodes.append(
                Node(
                    id=record["id"],
                    label=record["label"],
                    type=record["type"],
                    props=self._clean_properties(record["props"]),
                )
            )

        return nodes

    async def _fetch_edges(self, session: AsyncSession) -> list[Edge]:
        """Fetch edges from Neo4j database.

        Args:
            session: Active Neo4j session

        Returns:
            List of Edge objects from the database
        """
        query = """
        MATCH (a)-[r]->(b)
        RETURN toString(id(r)) AS id,
               toString(id(a)) AS source,
               toString(id(b)) AS target,
               type(r) AS type,
               type(r) AS label,
               properties(r) AS props
        LIMIT $limit
        """

        result = await session.run(query, limit=self._edge_limit)
        edges: list[Edge] = []

        async for record in result:
            edges.append(
                Edge(
                    id=record["id"],
                    source=record["source"],
                    target=record["target"],
                    type=record["type"],
                    label=record["label"],
                    props=self._clean_properties(record["props"]),
                )
            )

        return edges

    @staticmethod
    def _clean_properties(props: Any) -> dict[str, Any]:
        """Clean and normalize property dictionary from Neo4j.

        Args:
            props: Raw properties from Neo4j query result

        Returns:
            Clean dictionary of properties
        """
        if props is None:
            return {}
        return dict(props) if isinstance(props, dict) else {}

    async def close(self) -> None:
        """Close the Neo4j driver connection.

        Should be called when the adapter is no longer needed
        to free up database connections.
        """
        await self._driver.close()
