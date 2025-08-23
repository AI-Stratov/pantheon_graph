from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class Node(BaseModel):
    """Represents a node in the graph with properties and metadata.

    Attributes:
        id: Unique identifier for the node
        label: Human-readable label for display
        type: Optional type classification for the node
        props: Additional properties as key-value pairs
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=True,
    )

    id: str = Field(..., min_length=1, description="Unique node identifier")
    label: str = Field(..., min_length=1, description="Human-readable node label")
    type: str | None = Field(None, description="Node type classification")
    props: dict[str, Any] = Field(default_factory=dict, description="Additional node properties")


class Edge(BaseModel):
    """Represents a directed edge between two nodes in the graph.

    Attributes:
        id: Unique identifier for the edge
        source: ID of the source node
        target: ID of the target node
        label: Optional human-readable label for the relationship
        type: Optional type classification for the edge
        props: Additional properties as key-value pairs
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=True,
    )

    id: str = Field(..., min_length=1, description="Unique edge identifier")
    source: str = Field(..., min_length=1, description="Source node identifier")
    target: str = Field(..., min_length=1, description="Target node identifier")
    label: str | None = Field(None, description="Human-readable edge label")
    type: str | None = Field(None, description="Edge type classification")
    props: dict[str, Any] = Field(default_factory=dict, description="Additional edge properties")


class Graph(BaseModel):
    """Represents a complete graph with nodes and edges.

    Attributes:
        nodes: List of nodes in the graph
        edges: List of edges connecting the nodes
    """

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
    )

    nodes: list[Node] = Field(default_factory=list, description="Graph nodes")
    edges: list[Edge] = Field(default_factory=list, description="Graph edges")

    @property
    def node_count(self) -> int:
        """Returns the number of nodes in the graph."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Returns the number of edges in the graph."""
        return len(self.edges)

    def get_node_by_id(self, node_id: str) -> Node | None:
        """Retrieve a node by its ID."""
        return next((node for node in self.nodes if node.id == node_id), None)

    def get_edges_for_node(self, node_id: str) -> list[Edge]:
        """Get all edges connected to a specific node."""
        return [edge for edge in self.edges if edge.source == node_id or edge.target == node_id]
