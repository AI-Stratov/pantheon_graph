from typing import final

from application.ports import GraphCacheInterface
from domain.models import Graph


@final
class MemoryGraphCache(GraphCacheInterface):  # type: ignore[misc]
    """In-memory graph cache implementation for development and testing.

    This cache stores the graph data in application memory, making it
    suitable for development, testing, and single-instance deployments.
    Data will be lost when the application restarts.

    Attributes:
        _cached_graph: The currently cached graph data
    """

    def __init__(self) -> None:
        """Initialize empty memory cache."""
        self._cached_graph: Graph | None = None

    async def get(self) -> Graph | None:
        """Retrieve cached graph data from memory.

        Returns:
            Cached Graph object or None if no data is cached
        """
        return self._cached_graph

    async def set(self, graph: Graph) -> None:
        """Store graph data in memory cache.

        Args:
            graph: Graph object to cache in memory
        """
        self._cached_graph = graph

    def clear(self) -> None:
        """Clear all cached data from memory.

        Useful for testing and cache invalidation scenarios.
        """
        self._cached_graph = None

    @property
    def is_empty(self) -> bool:
        """Check if cache is empty.

        Returns:
            True if no graph is currently cached
        """
        return self._cached_graph is None
