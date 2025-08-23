from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import final

from application.ports import GraphCacheInterface
from domain.models import Graph, Node, Edge


class GraphAdapterInterface(ABC):
    """Abstract interface for graph data adapters.

    This interface provides a consistent contract for all external data sources
    (Neo4j, ArangoDB, Wikidata, etc.) that can provide graph data.
    """

    @abstractmethod
    async def get_graph(self) -> Graph:
        """Retrieve graph data from the external source.

        Returns:
            Complete Graph object with nodes and edges

        Raises:
            Exception: If data retrieval fails
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the external data source is accessible.

        Returns:
            True if the source is accessible and responding
        """
        ...


@final
class GraphAggregator:
    """Service for aggregating graph data from multiple adapters.

    This service combines data from multiple graph adapters, deduplicating
    nodes and edges by their IDs while preserving insertion order.

    Attributes:
        _adapters: List of graph adapters to aggregate data from
    """

    def __init__(self, adapters: Sequence[GraphAdapterInterface]) -> None:
        """Initialize the aggregator with a list of adapters.

        Args:
            adapters: Sequence of GraphAdapterInterface instances to aggregate
        """
        self._adapters = list(adapters)

    async def get_graph(self) -> Graph:
        """Aggregate graph data from all configured adapters.

        Combines data from multiple sources, deduplicating by ID.
        Later adapters can override earlier ones for the same ID.

        Returns:
            Aggregated Graph with deduplicated nodes and edges

        Raises:
            Exception: If any adapter fails to provide data
        """
        # Use regular dict to preserve insertion order and deduplicate by id
        nodes: dict[str, Node] = {}
        edges: dict[str, Edge] = {}

        for adapter in self._adapters:
            graph = await adapter.get_graph()

            # Add nodes, allowing later adapters to override earlier ones
            for node in graph.nodes:
                nodes[node.id] = node

            # Add edges, allowing later adapters to override earlier ones
            for edge in graph.edges:
                edges[edge.id] = edge

        return Graph(nodes=list(nodes.values()), edges=list(edges.values()))

    async def health_check_all(self) -> dict[str, bool]:
        """Check health status of all adapters.

        Returns:
            Dictionary mapping adapter class names to their health status
        """
        results: dict[str, bool] = {}
        for adapter in self._adapters:
            adapter_name = adapter.__class__.__name__
            try:
                results[adapter_name] = await adapter.health_check()
            except Exception:
                results[adapter_name] = False
        return results


@final
class GraphQueryService:
    """Application service for serving graph data with caching support.

    This service provides the main interface between the presentation layer
    and the domain logic, handling caching and data aggregation transparently.

    Attributes:
        _aggregator: Service for combining data from multiple sources
        _cache: Cache implementation for storing graph snapshots
    """

    def __init__(self, aggregator: GraphAggregator, cache: GraphCacheInterface) -> None:
        """Initialize the query service with aggregator and cache.

        Args:
            aggregator: GraphAggregator for combining data sources
            cache: GraphCacheInterface implementation for storing snapshots
        """
        self._aggregator = aggregator
        self._cache = cache

    async def get_graph(self, *, refresh: bool = False) -> Graph:
        """Retrieve graph data with optional cache refresh.

        Args:
            refresh: If True, bypass cache and fetch fresh data

        Returns:
            Complete Graph object with nodes and edges

        Raises:
            Exception: If data retrieval or caching fails
        """
        if not refresh:
            cached_graph = await self._cache.get()
            if cached_graph is not None:
                return cached_graph

        # Fetch fresh data and update cache
        fresh_graph = await self._aggregator.get_graph()
        await self._cache.set(fresh_graph)
        return fresh_graph

    async def health_check(self) -> dict[str, bool]:
        """Check health status of all underlying services.

        Returns:
            Dictionary with health status of adapters and cache
        """
        adapter_health = await self._aggregator.health_check_all()

        # Test cache health by attempting a get operation
        cache_healthy = True
        try:
            await self._cache.get()
        except Exception:
            cache_healthy = False

        return {
            'cache': cache_healthy,
            **adapter_health,
        }
