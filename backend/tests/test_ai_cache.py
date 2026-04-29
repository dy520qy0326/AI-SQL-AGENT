"""Tests for AI semantic cache."""

import uuid

import pytest

from app.ai.cache import (
    clear_all_cache,
    delete_expired_cache,
    get_cached,
    make_cache_key,
    set_cache,
)


def _unique_key():
    return uuid.uuid4().hex


class TestCacheKey:
    def test_same_inputs_produce_same_key(self):
        s = _unique_key()
        p = _unique_key()
        k1 = make_cache_key(s, p)
        k2 = make_cache_key(s, p)
        assert k1 == k2

    def test_different_inputs_produce_different_key(self):
        k1 = make_cache_key(_unique_key(), _unique_key())
        k2 = make_cache_key(_unique_key(), _unique_key())
        assert k1 != k2

    def test_key_is_64_char_hex(self):
        key = make_cache_key("abc", "def")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


class TestCacheSetAndGet:
    @pytest.mark.asyncio
    async def test_cache_hit(self, async_session):
        async with async_session.begin():
            cache_key = make_cache_key(_unique_key(), _unique_key())
            response = {"result": "test_value"}

            await set_cache(async_session, cache_key, _unique_key(), _unique_key(), response)
            cached = await get_cached(async_session, cache_key)
            assert cached == response

    @pytest.mark.asyncio
    async def test_cache_miss_unknown_key(self, async_session):
        async with async_session.begin():
            cached = await get_cached(async_session, _unique_key())
            assert cached is None

    @pytest.mark.asyncio
    async def test_expired_cache_not_returned(self, async_session):
        async with async_session.begin():
            cache_key = make_cache_key(_unique_key(), _unique_key())
            await set_cache(async_session, cache_key, _unique_key(), _unique_key(), {"val": 1}, ttl_hours=0)
            cached = await get_cached(async_session, cache_key)
            assert cached is None

    @pytest.mark.asyncio
    async def test_clear_all_removes_all(self, async_session):
        async with async_session.begin():
            k1 = make_cache_key(_unique_key(), _unique_key())
            k2 = make_cache_key(_unique_key(), _unique_key())
            await set_cache(async_session, k1, _unique_key(), _unique_key(), {"x": 1})
            await set_cache(async_session, k2, _unique_key(), _unique_key(), {"y": 2})

            assert await get_cached(async_session, k1) is not None
            assert await get_cached(async_session, k2) is not None

            deleted = await clear_all_cache(async_session)
            assert deleted >= 2
            assert await get_cached(async_session, k1) is None
            assert await get_cached(async_session, k2) is None

    @pytest.mark.asyncio
    async def test_delete_expired_only_removes_expired(self, async_session):
        async with async_session.begin():
            k_valid = make_cache_key(_unique_key(), _unique_key())
            k_expired = make_cache_key(_unique_key(), _unique_key())

            await set_cache(async_session, k_valid, _unique_key(), _unique_key(), {"v": 1}, ttl_hours=24)
            await set_cache(async_session, k_expired, _unique_key(), _unique_key(), {"v": 2}, ttl_hours=0)

            deleted = await delete_expired_cache(async_session)
            assert deleted == 1
            assert await get_cached(async_session, k_valid) is not None
            assert await get_cached(async_session, k_expired) is None

    @pytest.mark.asyncio
    async def test_schema_hash_change_produces_cache_miss(self, async_session):
        async with async_session.begin():
            k1 = make_cache_key(_unique_key(), _unique_key())
            k2 = make_cache_key(_unique_key(), _unique_key())

            await set_cache(async_session, k1, _unique_key(), _unique_key(), {"val": "old"})

            assert k1 != k2
            assert await get_cached(async_session, k2) is None
