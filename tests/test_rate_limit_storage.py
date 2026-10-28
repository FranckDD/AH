# tests/test_rate_limit_storage.py
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from limits.storage import MemoryStorage, RedisStorage

from api_backend.backend_app.rate_limit import build_limiter


def test_build_limiter_uses_redis_when_url_given():
    lim = build_limiter("redis://localhost:6379/0")
    assert isinstance(lim._storage, RedisStorage)


def test_build_limiter_uses_memory_without_url():
    for value in (None, ""):
        assert isinstance(build_limiter(value)._storage, MemoryStorage)
