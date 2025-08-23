from typing import final

from application.services import GraphAdapterInterface
from core.constants import NodeTypes, RelationshipTypes
from domain.models import Edge, Graph, Node


@final
class MemoryAdapter(GraphAdapterInterface):  # type: ignore[misc]
    """In-memory graph adapter for development and testing.

    This adapter provides static graph data stored in memory,
    useful for development, demos, and testing scenarios.

    Attributes:
        _graph: The static graph data to serve
    """

    def __init__(self, graph: Graph | None = None) -> None:
        """Initialize with optional custom graph data.

        Args:
            graph: Custom graph data, or None to use default Greek mythology data
        """
        self._graph = graph or self._create_default_graph()

    async def get_graph(self) -> Graph:
        """Retrieve the in-memory graph data.

        Returns:
            The stored Graph object
        """
        return self._graph

    async def health_check(self) -> bool:
        """Check adapter health (always healthy for memory adapter).

        Returns:
            Always True since memory is always accessible
        """
        return True

    @staticmethod
    def _create_default_graph() -> Graph:
        """Create default Greek mythology graph for demonstration.

        Returns:
            Graph with Greek gods/goddesses and their relationships
        """
        nodes = [
            Node(
                id="zeus",
                label="Zeus",
                type=NodeTypes.GOD,
                props={"domain": "sky", "realm": "olympus"}
            ),
            Node(
                id="hera",
                label="Hera",
                type=NodeTypes.GODDESS,
                props={"domain": "marriage", "realm": "olympus"}
            ),
            Node(
                id="poseidon",
                label="Poseidon",
                type=NodeTypes.GOD,
                props={"domain": "sea", "realm": "underwater"}
            ),
            Node(
                id="hades",
                label="Hades",
                type=NodeTypes.GOD,
                props={"domain": "underworld", "realm": "underworld"}
            ),
            Node(
                id="athena",
                label="Athena",
                type=NodeTypes.GODDESS,
                props={"domain": "wisdom", "realm": "olympus"}
            ),
            Node(
                id="aphrodite",
                label="Aphrodite",
                type=NodeTypes.GODDESS,
                props={"domain": "love", "realm": "olympus"}
            ),
        ]

        edges = [
            Edge(
                id="zeus-hera-spouse",
                source="zeus",
                target="hera",
                label=RelationshipTypes.SPOUSE,
                type=RelationshipTypes.SPOUSE
            ),
            Edge(
                id="hera-zeus-spouse",
                source="hera",
                target="zeus",
                label=RelationshipTypes.SPOUSE,
                type=RelationshipTypes.SPOUSE
            ),
            Edge(
                id="zeus-athena-parent",
                source="zeus",
                target="athena",
                label=RelationshipTypes.PARENT,
                type=RelationshipTypes.PARENT
            ),
            Edge(
                id="zeus-aphrodite-parent",
                source="zeus",
                target="aphrodite",
                label=RelationshipTypes.PARENT,
                type=RelationshipTypes.PARENT
            ),
            Edge(
                id="zeus-poseidon-sibling",
                source="zeus",
                target="poseidon",
                label=RelationshipTypes.SIBLING,
                type=RelationshipTypes.SIBLING
            ),
            Edge(
                id="zeus-hades-sibling",
                source="zeus",
                target="hades",
                label=RelationshipTypes.SIBLING,
                type=RelationshipTypes.SIBLING
            ),
        ]

        return Graph(nodes=nodes, edges=edges)
