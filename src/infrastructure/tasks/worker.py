from typing import Any

from application.ports import GraphCache
from application.services import GraphAggregator, GraphAdapter
from core.config import settings


def build_adapters() -> list[GraphAdapter]:
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


def build_cache() -> GraphCache:
    if settings.redis_dsn:
        from infrastructure.cache.redis import RedisGraphCache

        return RedisGraphCache(settings.redis_dsn)
    from infrastructure.cache.memory import MemoryGraphCache

    return MemoryGraphCache()


# TaskIQ broker configuration
try:
    from taskiq_redis import RedisBroker  # type: ignore
except Exception as exc:  # pragma: no cover - defensive
    raise RuntimeError(
        "taskiq-redis is required to run worker. Install optional deps and configure Redis."
    ) from exc


broker = RedisBroker(settings.redis_dsn or "redis://localhost:6379/0")


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
