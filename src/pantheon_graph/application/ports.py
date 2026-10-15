from typing import Protocol

from pantheon_graph.domain import Graph


class GraphSource(Protocol):
    """A backend able to produce a graph snapshot (database, API, bundled data...)."""

    @property
    def name(self) -> str: ...

    async def fetch(self) -> Graph: ...

    async def ping(self) -> bool: ...


class GraphCache(Protocol):
    """Storage for the latest aggregated graph snapshot."""

    async def get(self) -> Graph | None: ...

    async def set(self, graph: Graph) -> None: ...

    async def clear(self) -> None: ...

    async def ping(self) -> bool: ...
