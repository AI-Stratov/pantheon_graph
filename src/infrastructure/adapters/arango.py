from collections.abc import Sequence
from typing import final, Any

from anyio import to_thread
from arango import ArangoClient, Database  # type: ignore[attr-defined]

from application.services import GraphAdapterInterface
from core.config import ArangoConfig
from core.constants import DatabaseLimits
from domain.models import Edge, Graph, Node


@final
class ArangoAdapter(GraphAdapterInterface):  # type: ignore[misc]
    """ArangoDB adapter for graph data retrieval.

    This adapter supports two operational modes:
    1. Explicit collections: Uses specified vertex and edge collections
    2. Graph mode: Discovers collections from a named ArangoDB graph

    Since python-arango is synchronous, all database operations are
    offloaded to a thread pool to maintain async compatibility.

    Attributes:
        _config: ArangoDB connection configuration
        _client: ArangoDB client instance
        _database: Connected database instance
    """

    def __init__(self, config: ArangoConfig) -> None:
        """Initialize ArangoDB adapter with configuration.

        Args:
            config: ArangoDB connection and collection configuration
        """
        self._config = config
        self._client = ArangoClient(hosts=config.url)
        self._database: Database = self._client.db(
            config.db,
            username=config.user,
            password=config.password
        )

    async def get_graph(self) -> Graph:
        """Retrieve graph data from ArangoDB.

        Returns:
            Graph object containing nodes and edges from collections

        Raises:
            Exception: If database connection or queries fail
        """
        vertex_collections, edge_collections = await self._discover_collections()

        if not vertex_collections and not edge_collections:
            return Graph(nodes=[], edges=[])

        # Execute database operations in thread pool
        nodes = await to_thread.run_sync(
            lambda: self._fetch_vertices(vertex_collections)
        )
        edges = await to_thread.run_sync(
            lambda: self._fetch_edges(edge_collections)
        )

        return Graph(nodes=list(nodes.values()), edges=edges)

    async def health_check(self) -> bool:
        """Check if ArangoDB is accessible and responsive.

        Returns:
            True if database connection and queries work
        """
        try:
            # Test database connectivity in thread pool
            def test_connection() -> bool:
                try:
                    collections = self._database.collections()
                    return isinstance(collections, list)
                except Exception:
                    return False

            return await to_thread.run_sync(test_connection)
        except Exception:
            return False

    async def _discover_collections(self) -> tuple[list[str], list[str]]:
        """Discover vertex and edge collections to query.

        Returns:
            Tuple of (vertex_collections, edge_collections) lists
        """

        def discover() -> tuple[list[str], list[str]]:
            # Mode 1: Explicit collections specified
            if self._config.vertex_collection and self._config.edge_collection:
                return (
                    [self._config.vertex_collection],
                    [self._config.edge_collection]
                )

            # Mode 2: Discover from named graph
            if self._config.graph:
                try:
                    graph = self._database.graph(self._config.graph)
                    edge_definitions = graph.edge_definitions()

                    vertex_collections: set[str] = set()
                    edge_collections = [defn["edge_collection"] for defn in edge_definitions]

                    for defn in edge_definitions:
                        vertex_collections.update(defn.get("from_vertex_collections", []))
                        vertex_collections.update(defn.get("to_vertex_collections", []))

                    return (list(vertex_collections), edge_collections)
                except Exception:
                    # Graph doesn't exist or other error
                    return ([], [])

            # No configuration available
            return ([], [])

        return await to_thread.run_sync(discover)

    def _fetch_vertices(self, collections: Sequence[str]) -> dict[str, Node]:
        """Fetch vertex documents from specified collections.

        Args:
            collections: List of vertex collection names

        Returns:
            Dictionary mapping document IDs to Node objects
        """
        nodes: dict[str, Node] = {}

        for collection_name in collections:
            try:
                query = f"""
                FOR vertex IN {collection_name}
                LIMIT {DatabaseLimits.ARANGO_NODE_LIMIT}
                RETURN vertex
                """

                cursor = self._database.aql.execute(query)

                for document in cursor:
                    doc_id = document.get("_id")
                    if not doc_id or doc_id in nodes:
                        continue

                    # Extract meaningful label
                    label = self._extract_label(document, doc_id)

                    # Extract node type from collection name
                    node_type = doc_id.split("/")[0]

                    # Clean properties (exclude system fields)
                    props = self._clean_document_properties(document)

                    nodes[doc_id] = Node(
                        id=doc_id,
                        label=label,
                        type=node_type,
                        props=props
                    )

            except Exception:
                # Skip problematic collections
                continue

        return nodes

    def _fetch_edges(self, collections: Sequence[str]) -> list[Edge]:
        """Fetch edge documents from specified collections.

        Args:
            collections: List of edge collection names

        Returns:
            List of Edge objects
        """
        edges: list[Edge] = []

        for collection_name in collections:
            try:
                query = f"""
                FOR edge IN {collection_name}
                LIMIT {DatabaseLimits.ARANGO_EDGE_LIMIT}
                RETURN edge
                """

                cursor = self._database.aql.execute(query)

                for document in cursor:
                    doc_id = document.get("_id")
                    from_id = document.get("_from")
                    to_id = document.get("_to")

                    if not (doc_id and from_id and to_id):
                        continue

                    # Extract label and type
                    label = str(document.get("label", collection_name))
                    edge_type = collection_name

                    # Clean properties
                    props = self._clean_document_properties(document)

                    edges.append(
                        Edge(
                            id=doc_id,
                            source=from_id,
                            target=to_id,
                            label=label,
                            type=edge_type,
                            props=props
                        )
                    )

            except Exception:
                # Skip problematic collections
                continue

        return edges

    @staticmethod
    def _extract_label(document: dict[str, Any], fallback_id: str) -> str:
        """Extract a meaningful label from document fields.

        Args:
            document: ArangoDB document
            fallback_id: Fallback ID if no label fields found

        Returns:
            Human-readable label string
        """
        # Try common label fields in order of preference
        for field in ("name", "label", "title"):
            value = document.get(field)
            if value:
                return str(value)

        # Fall back to extracting key from document ID
        return fallback_id.split("/")[-1]

    @staticmethod
    def _clean_document_properties(document: dict[str, Any]) -> dict[str, Any]:
        """Remove system fields from ArangoDB document.

        Args:
            document: Raw ArangoDB document

        Returns:
            Clean properties dictionary without system fields
        """
        return {
            key: value
            for key, value in document.items()
            if not key.startswith("_")
        }
