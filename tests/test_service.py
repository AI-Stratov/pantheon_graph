import asyncio

import pytest

from pantheon_graph.application.aggregator import AllSourcesFailedError, GraphAggregator
from pantheon_graph.application.service import GraphService, HealthReport, HealthStatus
from pantheon_graph.domain import Graph
from pantheon_graph.infrastructure.cache.memory import MemoryCache
from tests.conftest import StubSource, make_graph

pytestmark = pytest.mark.anyio


async def test_aggregator_tolerates_partial_failure() -> None:
    sources = [StubSource(make_graph(['zeus'])), StubSource(error=ConnectionError('down'))]

    graph = await GraphAggregator(sources).fetch()

    assert [node.id for node in graph.nodes] == ['zeus']


async def test_aggregator_fails_when_every_source_fails() -> None:
    with pytest.raises(AllSourcesFailedError, match='down'):
        await GraphAggregator([StubSource(error=ConnectionError('down'))]).fetch()


async def test_aggregator_times_out_slow_sources() -> None:
    class SlowSource(StubSource):
        async def fetch(self) -> Graph:
            await asyncio.sleep(10)
            return Graph()

    sources = [StubSource(make_graph(['zeus'])), SlowSource()]

    graph = await GraphAggregator(sources, timeout=0.01).fetch()

    assert len(graph.nodes) == 1


async def test_aggregator_without_sources_returns_empty_graph() -> None:
    assert await GraphAggregator([]).fetch() == Graph()


async def test_service_caches_until_refresh() -> None:
    source = StubSource(make_graph(['zeus']))
    service = GraphService(GraphAggregator([source]), MemoryCache())

    await service.graph()
    await service.graph()
    assert source.calls == 1

    await service.refresh()
    assert source.calls == 2


async def test_service_rebuilds_once_for_concurrent_cold_requests() -> None:
    source = StubSource(make_graph(['zeus']))
    service = GraphService(GraphAggregator([source]), MemoryCache())

    await asyncio.gather(*(service.graph() for _ in range(5)))

    assert source.calls == 1


async def test_service_survives_broken_cache() -> None:
    class BrokenCache(MemoryCache):
        async def get(self) -> Graph | None:
            raise ConnectionError('redis down')

        async def set(self, graph: Graph) -> None:
            raise ConnectionError('redis down')

    service = GraphService(GraphAggregator([StubSource(make_graph(['zeus']))]), BrokenCache())

    assert len((await service.graph()).nodes) == 1
    assert (await service.health()).status is HealthStatus.OK


async def test_health_report() -> None:
    service = GraphService(
        GraphAggregator([StubSource(), StubSource(error=RuntimeError('boom'))]), MemoryCache()
    )

    report = await service.health()

    assert report.cache is True
    assert report.sources == {'stub': False}  # same name: the failing one reported last


@pytest.mark.parametrize(
    ('cache', 'sources', 'expected'),
    [
        (True, {'a': True, 'b': True}, HealthStatus.OK),
        (True, {'a': True, 'b': False}, HealthStatus.DEGRADED),
        (True, {'a': False}, HealthStatus.DOWN),
        (False, {'a': True}, HealthStatus.DOWN),
        (True, {}, HealthStatus.OK),
    ],
)
async def test_health_status(cache: bool, sources: dict[str, bool], expected: HealthStatus) -> None:
    assert HealthReport(cache=cache, sources=sources).status is expected
