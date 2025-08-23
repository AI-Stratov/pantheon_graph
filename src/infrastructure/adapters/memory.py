from application.services import GraphAdapter
from domain.models import Edge, Graph, Node


class MemoryAdapter(GraphAdapter):
    """Static in-memory graph adapter. Useful for development/demo.

    Consider replacing with Wikidata adapter in production demo.
    """

    def __init__(self, graph: Graph | None = None) -> None:
        self._graph = graph or self._default_graph()

    async def get_graph(self) -> Graph:
        return self._graph

    @staticmethod
    def _default_graph() -> Graph:
        nodes = [
            Node(id="zeus", label="Zeus", type="god", props={"domain": "sky"}),
            Node(id="hera", label="Hera", type="goddess", props={"domain": "marriage"}),
            Node(id="poseidon", label="Poseidon", type="god", props={"domain": "sea"}),
            Node(id="hades", label="Hades", type="god", props={"domain": "underworld"}),
            Node(id="athena", label="Athena", type="goddess", props={"domain": "wisdom"}),
            Node(id="aphrodite", label="Aphrodite", type="goddess", props={"domain": "love"}),
        ]
        edges = [
            Edge(id="zeus-hera-spouse", source="zeus", target="hera", label="spouse", type="spouse"),
            Edge(id="hera-zeus-spouse", source="hera", target="zeus", label="spouse", type="spouse"),
            Edge(id="zeus-athena-parent", source="zeus", target="athena", label="parent", type="parent"),
            Edge(id="zeus-aphrodite-parent", source="zeus", target="aphrodite", label="parent", type="parent"),
            Edge(id="zeus-poseidon-sibling", source="zeus", target="poseidon", label="sibling", type="sibling"),
            Edge(id="zeus-hades-sibling", source="zeus", target="hades", label="sibling", type="sibling"),
        ]
        return Graph(nodes=nodes, edges=edges)
