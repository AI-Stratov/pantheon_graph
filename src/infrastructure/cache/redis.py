from typing import Any

from application.ports import GraphCache
from domain.models import Graph


class RedisGraphCache(GraphCache):
    """Redis-based Graph cache using redis.asyncio client.

    This implementation stores the whole graph as JSON under a single key.
    """

    def __init__(self, dsn: str, key: str = "pantheon:graph") -> None:
        # Lazy import to avoid dependency unless used.
        import redis.asyncio as redis  # type: ignore

        self._redis: Any = redis.from_url(dsn, decode_responses=True)
        self._key = key

    async def get(self) -> Graph | None:
        raw = await self._redis.get(self._key)
        if not raw:
            return None
        return Graph.model_validate_json(raw)

    async def set(self, graph: Graph) -> None:
        await self._redis.set(self._key, graph.model_dump_json())
