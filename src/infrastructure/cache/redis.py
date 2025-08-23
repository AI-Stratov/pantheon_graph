from typing import final

import redis.asyncio as redis

from application.ports import GraphCacheInterface
from core.constants import CacheKeys
from domain.models import Graph


@final
class RedisGraphCache(GraphCacheInterface):  # type: ignore[misc]
    """Redis-based graph cache implementation for production environments.

    This cache stores graph data in Redis as JSON, making it suitable
    for distributed deployments and persistent caching across restarts.

    Attributes:
        _redis: Redis async client instance
        _cache_key: Redis key used for storing graph data
    """

    def __init__(
            self,
            redis_client: redis.Redis,
            cache_key: str = CacheKeys.DEFAULT_GRAPH_KEY
    ) -> None:
        """Initialize Redis cache with connection and key configuration.

        Args:
            redis_client: Configured Redis async client
            cache_key: Redis key for storing graph data
        """
        self._redis = redis_client
        self._cache_key = cache_key

    async def get(self) -> Graph | None:
        """Retrieve cached graph data from Redis.

        Returns:
            Cached Graph object or None if not found or invalid

        Raises:
            Exception: If Redis connection fails or data is corrupted
        """
        try:
            raw_data = await self._redis.get(self._cache_key)
            if not raw_data:
                return None

            return Graph.model_validate_json(raw_data)
        except Exception:
            # Log error in production, but don't fail the request
            return None

    async def set(self, graph: Graph) -> None:
        """Store graph data in Redis cache.

        Args:
            graph: Graph object to cache

        Raises:
            Exception: If Redis connection fails or serialization fails
        """
        json_data = graph.model_dump_json()
        await self._redis.set(self._cache_key, json_data)

    async def clear(self) -> None:
        """Clear cached graph data from Redis.

        Useful for cache invalidation and testing scenarios.

        Raises:
            Exception: If Redis connection fails
        """
        await self._redis.delete(self._cache_key)

    async def exists(self) -> bool:
        """Check if cached data exists in Redis.

        Returns:
            True if cache key exists in Redis

        Raises:
            Exception: If Redis connection fails
        """
        result = await self._redis.exists(self._cache_key)
        return bool(result)

    async def ttl(self) -> int:
        """Get time-to-live for cached data.

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist

        Raises:
            Exception: If Redis connection fails
        """
        result = await self._redis.ttl(self._cache_key)
        return int(result)

    async def set_with_expiry(self, graph: Graph, ttl_seconds: int) -> None:
        """Store graph data with expiration time.

        Args:
            graph: Graph object to cache
            ttl_seconds: Time-to-live in seconds

        Raises:
            Exception: If Redis connection fails
        """
        json_data = graph.model_dump_json()
        await self._redis.setex(self._cache_key, ttl_seconds, json_data)

    async def close(self) -> None:
        """Close Redis connection.

        Should be called when cache is no longer needed to free resources.
        """
        await self._redis.close()
