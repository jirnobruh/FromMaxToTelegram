"""
Thread-safe Async User Cache with TTL to reduce RPC calls for author names.
"""
import asyncio
import time
from typing import Optional


class CacheEntry:
    def __init__(self, value: str, expire_at: float):
        self.value = value
        self.expire_at = expire_at

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expire_at

    @property
    def display_name(self) -> str:
        return self.value


UserCacheEntry = CacheEntry


class AsyncTTLCache:
    """In-memory thread-safe generic cache with TTL."""

    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: int | str) -> Optional[str]:
        k = str(key)
        async with self._lock:
            entry = self._cache.get(k)
            if entry is None:
                return None
            if entry.is_expired:
                del self._cache[k]
                return None
            return entry.value

    async def set(self, key: int | str, value: str) -> None:
        k = str(key)
        async with self._lock:
            self._cache[k] = CacheEntry(
                value=value,
                expire_at=time.time() + self.ttl,
            )

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()


class UserCache(AsyncTTLCache):
    """In-memory thread-safe user display name cache with TTL."""
    pass


class ChatCache(AsyncTTLCache):
    """In-memory thread-safe chat title cache with TTL."""
    pass

