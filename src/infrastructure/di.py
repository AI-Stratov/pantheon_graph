from dishka import Provider, Scope, provide

from application.ports import GraphCache
from application.services import GraphAggregator, GraphAdapter, GraphQueryService
from core.config import settings


class AppProvider(Provider):
    """DI wiring: compose adapters, cache and services."""

    @provide(scope=Scope.APP)
    def get_adapters(self) -> list[GraphAdapter]:
        adapters: list[GraphAdapter] = []
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

            adapters.append(WikidataAdapter(settings.wikidata_endpoint, settings.wikidata_user_agent))
        return adapters

    @provide(scope=Scope.APP)
    def get_cache(self) -> GraphCache:
        if settings.redis_dsn:
            from infrastructure.cache.redis import RedisGraphCache

            return RedisGraphCache(settings.redis_dsn)
        from infrastructure.cache.memory import MemoryGraphCache

        return MemoryGraphCache()

    @provide(scope=Scope.REQUEST)
    async def get_aggregator(self, adapters: list[GraphAdapter]) -> GraphAggregator:
        return GraphAggregator(adapters)

    @provide(scope=Scope.REQUEST)
    async def get_query_service(self, aggregator: GraphAggregator, cache: GraphCache) -> GraphQueryService:
        return GraphQueryService(aggregator, cache)
