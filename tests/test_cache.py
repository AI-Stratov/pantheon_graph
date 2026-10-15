import pytest

from pantheon_graph.infrastructure.cache.memory import MemoryCache
from pantheon_graph.infrastructure.cache.redis import RedisCache
from tests.conftest import make_graph

pytestmark = pytest.mark.anyio


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}
        self.ttl: dict[str, int | None] = {}

    async def get(self, key: str) -> bytes | None:
        return self.data.get(key)

    async def set(self, key: str, value: bytes, ex: int | None = None) -> None:
        self.data[key] = value
        self.ttl[key] = ex

    async def delete(self, key: str) -> None:
        self.data.pop(key, None)

    async def ping(self) -> bool:
        return True


async def test_memory_cache_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [100.0]
    monkeypatch.setattr(
        'pantheon_graph.infrastructure.cache.memory.time.monotonic', lambda: clock[0]
    )
    cache = MemoryCache(ttl=10)
    await cache.set(make_graph(['zeus']))

    assert await cache.get() is not None
    clock[0] += 10
    assert await cache.get() is None


async def test_redis_cache_round_trip() -> None:
    redis = FakeRedis()
    cache = RedisCache(redis, key='k', ttl=60)  # type: ignore[arg-type]
    graph = make_graph(['zeus', 'hera'], [('zeus', 'hera', 'spouse')])

    await cache.set(graph)

    assert await cache.get() == graph
    assert redis.ttl['k'] == 60


async def test_redis_cache_drops_corrupted_entry() -> None:
    redis = FakeRedis()
    redis.data['k'] = b'{"not": "a graph"'
    cache = RedisCache(redis, key='k')  # type: ignore[arg-type]

    assert await cache.get() is None
    assert 'k' not in redis.data
