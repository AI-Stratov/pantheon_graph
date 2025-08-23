from typing import Protocol

from domain.models import Graph


class GraphCache(Protocol):
    """Abstract cache for storing the latest Graph snapshot."""

    async def get(self) -> Graph | None:  # pragma: no cover - interface
        raise NotImplementedError

    async def set(self, graph: Graph) -> None:  # pragma: no cover - interface
        raise NotImplementedError

