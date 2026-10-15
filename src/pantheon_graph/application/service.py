import asyncio
import logging
from dataclasses import dataclass
from enum import StrEnum

from pantheon_graph.application.aggregator import GraphAggregator
from pantheon_graph.application.ports import GraphCache
from pantheon_graph.domain import Graph, GraphStats, Node

logger = logging.getLogger(__name__)


class HealthStatus(StrEnum):
    OK = 'ok'
    DEGRADED = 'degraded'
    DOWN = 'down'


@dataclass(frozen=True, slots=True)
class HealthReport:
    cache: bool
    sources: dict[str, bool]

    @property
    def status(self) -> HealthStatus:
        if not self.cache or (self.sources and not any(self.sources.values())):
            return HealthStatus.DOWN
        if all(self.sources.values()):
            return HealthStatus.OK
        return HealthStatus.DEGRADED


class GraphService:
    """Serves the aggregated graph through a read-through cache."""

    def __init__(self, aggregator: GraphAggregator, cache: GraphCache) -> None:
        self._aggregator = aggregator
        self._cache = cache
        self._lock = asyncio.Lock()

    async def graph(self) -> Graph:
        if (cached := await self._cached()) is not None:
            return cached
        async with self._lock:  # one rebuild at a time on a cold cache
            if (cached := await self._cached()) is not None:
                return cached
            return await self._rebuild()

    async def refresh(self) -> Graph:
        async with self._lock:
            return await self._rebuild()

    async def neighbourhood(self, node_id: str, depth: int = 1) -> Graph:
        return (await self.graph()).neighbourhood(node_id, depth)

    async def path(self, source: str, target: str) -> Graph:
        return (await self.graph()).shortest_path(source, target)

    async def relationships(
        self,
        *,
        node: str | None = None,
        source: str | None = None,
        target: str | None = None,
        kind: str | None = None,
        label: str | None = None,
    ) -> Graph:
        graph = await self.graph()
        return graph.filter_edges(node=node, source=source, target=target, kind=kind, label=label)

    async def search(self, query: str, limit: int = 20) -> list[Node]:
        return (await self.graph()).search(query, limit)

    async def stats(self) -> GraphStats:
        return (await self.graph()).stats()

    async def health(self) -> HealthReport:
        cache_ok, sources = await asyncio.gather(self._ping_cache(), self._aggregator.ping())
        return HealthReport(cache=cache_ok, sources=sources)

    async def _rebuild(self) -> Graph:
        graph = await self._aggregator.fetch()
        try:
            await self._cache.set(graph)
        except Exception:
            logger.exception('Could not store graph in cache')
        logger.info('Graph rebuilt: %d nodes, %d edges', len(graph.nodes), len(graph.edges))
        return graph

    async def _cached(self) -> Graph | None:
        try:
            return await self._cache.get()
        except Exception:
            logger.exception('Could not read graph from cache')
            return None

    async def _ping_cache(self) -> bool:
        try:
            return await self._cache.ping()
        except Exception:
            return False
