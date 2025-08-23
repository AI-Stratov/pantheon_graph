from application.ports import GraphCache
from domain.models import Graph


class MemoryGraphCache(GraphCache):
    """In-memory Graph cache. Useful for development/testing."""

    def __init__(self) -> None:
        self._graph: Graph | None = None

    async def get(self) -> Graph | None:
        return self._graph

    async def set(self, graph: Graph) -> None:
        self._graph = graph

