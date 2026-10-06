"""
Thread-safe Async User Cache with TTL to reduce RPC calls for author names.
"""
import asyncio
import time
from typing import Optional


class UserCacheEntry:
    def __init__(self, display_name: str, expire_at: float):
        self.display_name = display_name
        self.expire_at = expire_at

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expire_at


class UserCache:
    """In-memory thread-safe user cache with TTL."""

    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self._cache: dict[str, UserCacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, user_id: int | str) -> Optional[str]:
        key = str(user_id)
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.is_expired:
                del self._cache[key]
                return None
            return entry.display_name

    async def set(self, user_id: int | str, display_name: str) -> None:
        key = str(user_id)
        async with self._lock:
            self._cache[key] = UserCacheEntry(
                display_name=display_name,
                expire_at=time.time() + self.ttl,
            )

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
