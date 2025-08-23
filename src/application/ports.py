from typing import Protocol

from domain.models import Graph


class GraphCacheInterface(Protocol):
    """Protocol interface for caching graph data with type-safe contract.

    This protocol defines the contract for any cache implementation
    that can store and retrieve Graph objects.
    """

    async def get(self) -> Graph | None:
        """Retrieve cached graph data.

        Returns:
            Cached Graph object or None if not found or expired
        """
        ...

    async def set(self, graph: Graph) -> None:
        """Store graph data in cache.

        Args:
            graph: Graph object to cache
        """
        ...
