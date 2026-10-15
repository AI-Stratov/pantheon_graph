import asyncio
import logging
from collections.abc import Sequence

from pantheon_graph.application.ports import GraphSource
from pantheon_graph.domain import Graph

logger = logging.getLogger(__name__)


class AllSourcesFailedError(RuntimeError):
    """Every configured source failed, so there is no graph to serve."""


class GraphAggregator:
    """Queries all sources concurrently and merges their snapshots.

    A failing or slow source is logged and skipped as long as at least one
    other source succeeds, so one flaky backend never takes the UI down.
    """

    def __init__(self, sources: Sequence[GraphSource], *, timeout: float = 30.0) -> None:
        self._sources = tuple(sources)
        self._timeout = timeout

    @property
    def sources(self) -> tuple[GraphSource, ...]:
        return self._sources

    async def fetch(self) -> Graph:
        if not self._sources:
            return Graph()

        results = await asyncio.gather(
            *(self._fetch_one(source) for source in self._sources), return_exceptions=True
        )

        graphs: list[Graph] = []
        errors: list[str] = []
        for source, result in zip(self._sources, results, strict=True):
            match result:
                case Graph():
                    graphs.append(result)
                case Exception():
                    logger.warning('Source %r failed: %r', source.name, result)
                    errors.append(f'{source.name}: {result!r}')
                case _:
                    raise result  # CancelledError / KeyboardInterrupt must propagate

        if not graphs:
            raise AllSourcesFailedError('All graph sources failed: ' + '; '.join(errors))
        return Graph.merge(graphs)

    async def ping(self) -> dict[str, bool]:
        async def ping_one(source: GraphSource) -> bool:
            try:
                async with asyncio.timeout(self._timeout):
                    return await source.ping()
            except Exception:
                logger.warning('Health check of %r failed', source.name, exc_info=True)
                return False

        statuses = await asyncio.gather(*(ping_one(source) for source in self._sources))
        return {source.name: ok for source, ok in zip(self._sources, statuses, strict=True)}

    async def _fetch_one(self, source: GraphSource) -> Graph:
        async with asyncio.timeout(self._timeout):
            return await source.fetch()
