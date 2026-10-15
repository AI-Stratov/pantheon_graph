import time

from pantheon_graph.domain import Graph


class MemoryCache:
    """Process-local cache: fine for a single instance, lost on restart."""

    def __init__(self, ttl: int | None = None) -> None:
        self._ttl = ttl
        self._graph: Graph | None = None
        self._expires_at = float('inf')

    async def get(self) -> Graph | None:
        if time.monotonic() >= self._expires_at:
            await self.clear()
        return self._graph

    async def set(self, graph: Graph) -> None:
        self._graph = graph
        self._expires_at = time.monotonic() + self._ttl if self._ttl else float('inf')

    async def clear(self) -> None:
        self._graph = None
        self._expires_at = float('inf')

    async def ping(self) -> bool:
        return True
