from typing import Any

import redis.asyncio as redis

from application.ports import GraphCacheInterface
from application.services import GraphAggregator, GraphAdapterInterface
from core.config import settings


def build_adapters() -> list[GraphAdapterInterface]:
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

        adapters.append(WikidataAdapter(settings.wikidata_endpoint, settings.wikidata_user_agent))
    return adapters


def build_cache() -> GraphCacheInterface:
    if settings.redis_dsn:
        from infrastructure.cache.redis import RedisGraphCache

        redis_client = redis.from_url(settings.redis_dsn, decode_responses=True)  # type: ignore[no-untyped-call]
        return RedisGraphCache(redis_client)
    from infrastructure.cache.memory import MemoryGraphCache

    return MemoryGraphCache()


# TaskIQ broker configuration
try:
    from taskiq_redis import RedisStreamBroker
except Exception as exc:  # pragma: no cover - defensive
    raise RuntimeError(
        "taskiq-redis is required to run worker. Install optional deps and configure Redis."
    ) from exc

broker = RedisStreamBroker(settings.redis_dsn or "redis://localhost:6379/0")


@broker.task
async def refresh_graph_task() -> dict[str, Any]:
    """Fetch graph from adapters and cache it.

    Returns basic stats for logging/observability.
    """
    aggregator = GraphAggregator(build_adapters())
    cache = build_cache()
    graph = await aggregator.get_graph()
    await cache.set(graph)
    return {"nodes": len(graph.nodes), "edges": len(graph.edges)}
