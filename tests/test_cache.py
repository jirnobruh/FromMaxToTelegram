"""
Unit tests for user caching behavior.
"""
import asyncio
import pytest
from src.cache import UserCache


@pytest.mark.asyncio
async def test_user_cache_set_and_get():
    cache = UserCache(ttl=10)
    await cache.set(123, "Иван")
    assert await cache.get(123) == "Иван"
    assert await cache.get("123") == "Иван"
    assert await cache.get(999) is None


@pytest.mark.asyncio
async def test_user_cache_expiration():
    cache = UserCache(ttl=0)  # Immediate expiry
    await cache.set(456, "Пётр")
    # Small sleep to ensure time passes
    await asyncio.sleep(0.01)
    assert await cache.get(456) is None
