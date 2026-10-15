import logging

from pydantic import TypeAdapter, ValidationError
from redis.asyncio import Redis

from pantheon_graph.domain import Graph

logger = logging.getLogger(__name__)

_codec = TypeAdapter(Graph)


class RedisCache:
    """Shared cache so every web instance and the worker see the same snapshot."""

    def __init__(
        self, redis: Redis, *, key: str = 'pantheon:graph', ttl: int | None = None
    ) -> None:
        self._redis = redis
        self._key = key
        self._ttl = ttl

    async def get(self) -> Graph | None:
        raw: bytes | str | None = await self._redis.get(self._key)
        if raw is None:
            return None
        try:
            return _codec.validate_json(raw)
        except ValidationError:
            logger.warning('Dropping unreadable cache entry %r', self._key)
            await self.clear()
            return None

    async def set(self, graph: Graph) -> None:
        await self._redis.set(self._key, _codec.dump_json(graph), ex=self._ttl)

    async def clear(self) -> None:
        await self._redis.delete(self._key)

    async def ping(self) -> bool:
        return bool(await self._redis.ping())
