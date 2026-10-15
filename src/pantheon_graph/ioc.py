"""Dependency injection wiring shared by the web app and the worker."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack

from dishka import AsyncContainer, Provider, Scope, from_context, make_async_container, provide

from pantheon_graph.application.aggregator import GraphAggregator
from pantheon_graph.application.ports import GraphCache, GraphSource
from pantheon_graph.application.service import GraphService
from pantheon_graph.config import Settings
from pantheon_graph.infrastructure.cache.memory import MemoryCache
from pantheon_graph.infrastructure.sources.factory import open_sources


class GraphProvider(Provider):
    # Everything is a singleton: sources own connection pools and the
    # service lock must be shared by all requests.
    scope = Scope.APP

    settings = from_context(provides=Settings)

    @provide
    async def sources(self, settings: Settings) -> AsyncIterator[list[GraphSource]]:
        async with AsyncExitStack() as stack:
            yield await open_sources(settings, stack)

    @provide
    async def cache(self, settings: Settings) -> AsyncIterator[GraphCache]:
        if not settings.redis_url:
            yield MemoryCache(ttl=settings.cache_ttl)
            return

        from redis.asyncio import Redis

        from pantheon_graph.infrastructure.cache.redis import RedisCache

        async with Redis.from_url(settings.redis_url) as redis:
            yield RedisCache(redis, ttl=settings.cache_ttl)

    @provide
    def aggregator(self, sources: list[GraphSource], settings: Settings) -> GraphAggregator:
        return GraphAggregator(sources, timeout=settings.source_timeout)

    service = provide(GraphService)


def make_container(settings: Settings, *providers: Provider) -> AsyncContainer:
    return make_async_container(GraphProvider(), *providers, context={Settings: settings})
