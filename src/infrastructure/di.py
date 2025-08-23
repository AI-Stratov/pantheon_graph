import redis.asyncio as redis
from dishka import Provider, Scope, provide

from application.ports import GraphCacheInterface
from application.services import GraphAggregator, GraphAdapterInterface, GraphQueryService
from core.config import settings


class AppProvider(Provider):
    """DI wiring: compose adapters, cache and services."""

    @provide(scope=Scope.APP)
    def get_adapters(self) -> list[GraphAdapterInterface]:
        """Create and configure all enabled graph adapters."""
        adapters: list[GraphAdapterInterface] = []

        if settings.enable_memory_adapter:
            from infrastructure.adapters.memory import MemoryAdapter
            adapters.append(MemoryAdapter())

        if settings.enable_neo4j_adapter and settings.neo4j:
            from infrastructure.adapters.neo4j import Neo4jAdapter
            adapters.append(Neo4jAdapter(settings.neo4j))

        if settings.enable_arango_adapter and settings.arango:
            from infrastructure.adapters.arango import ArangoAdapter
            adapters.append(ArangoAdapter(settings.arango))

        if settings.enable_wikidata_adapter:
            from infrastructure.adapters.wikidata import WikidataAdapter
            adapters.append(WikidataAdapter(
                settings.wikidata_endpoint,
                settings.wikidata_user_agent
            ))

        return adapters

    @provide(scope=Scope.APP)
    def get_redis_client(self) -> redis.Redis | None:
        """Create Redis client if configured."""
        if not settings.redis_dsn:
            return None
        client: redis.Redis = redis.from_url(settings.redis_dsn, decode_responses=True)  # type: ignore[no-untyped-call]
        return client

    @provide(scope=Scope.APP)
    def get_cache(self, redis_client: redis.Redis | None) -> GraphCacheInterface:
        """Create appropriate cache implementation based on configuration."""
        if redis_client is not None:
            from infrastructure.cache.redis import RedisGraphCache
            return RedisGraphCache(redis_client)

        from infrastructure.cache.memory import MemoryGraphCache
        return MemoryGraphCache()

    @provide(scope=Scope.REQUEST)
    async def get_aggregator(self, adapters: list[GraphAdapterInterface]) -> GraphAggregator:
        """Create graph aggregator service."""
        return GraphAggregator(adapters)

    @provide(scope=Scope.REQUEST)
    async def get_query_service(
            self,
            aggregator: GraphAggregator,
            cache: GraphCacheInterface
    ) -> GraphQueryService:
        """Create graph query service."""
        return GraphQueryService(aggregator, cache)
