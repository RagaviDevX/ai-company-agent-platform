"""Redis-backed cache with an automatic in-memory fallback.

Caching is always an optimization here, never a hard dependency: if
REDIS_URL isn't set, the `redis` package isn't installed, or the server
isn't reachable at startup, the cache silently falls back to a
process-local in-memory store instead of failing requests.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any

from backend.config.settings import settings
from backend.utils.logger import write_log

try:
    import redis as _redis
except ImportError:  # redis is an optional dependency
    _redis = None


class _InMemoryCache:
    """Simple process-local TTL cache used when Redis isn't available.

    Not shared across worker processes -- fine for a single-process dev
    server, and still a real hit-rate win for repeated identical queries
    within one process even in a multi-worker deployment.
    """

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at < time.time():
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        with self._lock:
            self._data[key] = (time.time() + ttl_seconds, value)


class Cache:
    def __init__(self) -> None:
        self._backend = "memory"
        self._memory = _InMemoryCache()
        self._client = None
        if settings.redis_url and _redis is not None:
            try:
                client = _redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
                client.ping()
                self._client = client
                self._backend = "redis"
            except Exception as exc:
                write_log({"cache": "redis_unavailable", "error": str(exc)})
        elif settings.redis_url and _redis is None:
            write_log({"cache": "redis_package_not_installed"})

    @property
    def backend(self) -> str:
        """'redis' or 'memory' -- surfaced on /health for operators."""
        return self._backend

    def get_json(self, key: str) -> Any | None:
        raw = self._get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self._set(key, json.dumps(value), ttl_seconds or settings.cache_ttl_seconds)

    def _get(self, key: str) -> str | None:
        if self._client is not None:
            try:
                raw = self._client.get(key)
                return raw.decode("utf-8") if raw is not None else None
            except Exception as exc:
                write_log({"cache": "redis_get_failed", "error": str(exc)})
        return self._memory.get(key)

    def _set(self, key: str, value: str, ttl_seconds: int) -> None:
        if self._client is not None:
            try:
                self._client.setex(key, ttl_seconds, value)
                return
            except Exception as exc:
                write_log({"cache": "redis_set_failed", "error": str(exc)})
        self._memory.set(key, value, ttl_seconds)


_CACHE: Cache | None = None


def get_cache() -> Cache:
    global _CACHE
    if _CACHE is None:
        _CACHE = Cache()
    return _CACHE