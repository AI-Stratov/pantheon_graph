from abc import ABC, abstractmethod

from domain.models import Graph, Node, Edge
from application.ports import GraphCache


class GraphAdapter(ABC):

    @abstractmethod
    async def get_graph(self) -> Graph:  # pragma: no cover - interface-like base
        raise NotImplementedError


class GraphAggregator:
    def __init__(self, adapters: list[GraphAdapter]):
        self._adapters = adapters

    async def get_graph(self) -> Graph:
        # Use regular dict to preserve insertion order and deduplicate by id.
        nodes: dict[str, Node] = {}
        edges: dict[str, Edge] = {}

        for adapter in self._adapters:
            g = await adapter.get_graph()
            for n in g.nodes:
                nodes.setdefault(n.id, n)
            for e in g.edges:
                edges.setdefault(e.id, e)
        return Graph(nodes=list(nodes.values()), edges=list(edges.values()))


class GraphQueryService:
    """Application service to serve Graph to presentation layer with caching."""

    def __init__(self, aggregator: GraphAggregator, cache: GraphCache):
        self._aggregator = aggregator
        self._cache = cache

    async def get_graph(self, refresh: bool = False) -> Graph:
        if not refresh:
            cached = await self._cache.get()
            if cached is not None:
                return cached
        graph = await self._aggregator.get_graph()
        await self._cache.set(graph)
        return graph
