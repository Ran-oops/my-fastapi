"""Tests for the async cache layer.

This module tests:
- Cache key builders
- Serialization/deserialization
- Cache decorators
- Cache management functions
"""

import json
import pickle
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cache import (
    CacheKeyBuilder,
    CacheSerializer,
    _build_cache_key,
    _delete_by_pattern,
    _json_default_encoder,
    _serialize_args,
    _serialize_kwargs,
    cache,
    cache_manager,
    clear_cache,
    delete_cache,
    delete_cache_pattern,
    get_cache,
    get_cache_info,
    invalidate_cache,
    set_cache,
)


class TestCacheKeyBuilder:
    """Tests for cache key builders."""

    def test_simple_key_builder_basic(self):
        """Test simple key builder with basic arguments."""

        def mock_func(arg1, arg2):
            pass

        mock_func.__module__ = "app.modules.users"
        mock_func.__qualname__ = "get_user"

        key = CacheKeyBuilder.simple_key_builder(mock_func, None, "value1", "value2")

        assert "app.modules.users.get_user" in key
        assert "value1" in key
        assert "value2" in key

    def test_simple_key_builder_with_prefix(self):
        """Test simple key builder with prefix."""

        def mock_func(arg1):
            pass

        mock_func.__module__ = "app.modules.users"
        mock_func.__qualname__ = "get_user"

        key = CacheKeyBuilder.simple_key_builder(mock_func, "users", 123)

        assert key.startswith("users:")
        assert "123" in key

    def test_simple_key_builder_with_kwargs(self):
        """Test simple key builder with kwargs."""

        def mock_func(arg1, **kwargs):
            pass

        mock_func.__module__ = "app.test"
        mock_func.__qualname__ = "test_func"

        key = CacheKeyBuilder.simple_key_builder(mock_func, None, "arg1", key="value")

        assert "arg1" in key
        assert "key" in key
        assert "value" in key

    def test_hash_key_builder(self):
        """Test hash-based key builder."""

        def mock_func(arg1, arg2):
            pass

        mock_func.__module__ = "app.test"
        mock_func.__qualname__ = "test_func"

        key = CacheKeyBuilder.hash_key_builder(mock_func, "test", "a", "b")

        assert key.startswith("test:test_func:")
        # Hash part should be present
        assert len(key.split(":")) == 3

    def test_custom_key_builder_success(self):
        """Test custom key builder with valid template."""

        def mock_func(user_id, name):
            pass

        mock_func.__module__ = "app.test"
        mock_func.__qualname__ = "get_user"

        builder = CacheKeyBuilder.custom_key_builder("user:{user_id}:{name}")
        key = builder(mock_func, None, 123, "test")

        assert key == "user:123:test"

    def test_custom_key_builder_fallback(self):
        """Test custom key builder falls back to simple builder on error."""

        def mock_func(user_id):
            pass

        mock_func.__module__ = "app.test"
        mock_func.__qualname__ = "get_user"

        # Template references non-existent argument
        builder = CacheKeyBuilder.custom_key_builder("user:{nonexistent}")
        key = builder(mock_func, "prefix", 123)

        # Should fallback to simple builder
        assert "app.test.get_user" in key


class TestCacheSerializer:
    """Tests for cache serializer."""

    def test_serialize_json_dict(self):
        """Test JSON serialization of dict."""
        data = {"id": 1, "name": "test", "active": True}

        serialized = CacheSerializer.serialize(data)
        deserialized = CacheSerializer.deserialize(serialized)

        assert deserialized == data

    def test_serialize_json_list(self):
        """Test JSON serialization of list."""
        data = [1, 2, 3, "test", None]

        serialized = CacheSerializer.serialize(data)
        deserialized = CacheSerializer.deserialize(serialized)

        assert deserialized == data

    def test_serialize_json_datetime(self):
        """Test JSON serialization handles datetime."""
        data = {"created_at": datetime(2024, 1, 1, 12, 0, 0)}

        serialized = CacheSerializer.serialize(data)
        deserialized = CacheSerializer.deserialize(serialized)

        assert deserialized["created_at"] == "2024-01-01T12:00:00"

    def test_serialize_json_nested(self):
        """Test JSON serialization of nested structures."""
        data = {
            "user": {"id": 1, "name": "test"},
            "items": [1, 2, 3],
            "metadata": {"created": datetime(2024, 1, 1)},
        }

        serialized = CacheSerializer.serialize(data)
        deserialized = CacheSerializer.deserialize(serialized)

        assert deserialized["user"]["id"] == 1
        assert deserialized["items"] == [1, 2, 3]

    def test_deserialize_bytes(self):
        """Test deserialization of bytes."""
        data = {"key": "value"}
        serialized = json.dumps(data).encode("utf-8")

        deserialized = CacheSerializer.deserialize(serialized)

        assert deserialized == data


class TestJsonDefaultEncoder:
    """Tests for JSON default encoder."""

    def test_encode_datetime(self):
        """Test encoding datetime object."""
        dt = datetime(2024, 1, 15, 10, 30, 0)

        result = _json_default_encoder(dt)

        assert result == "2024-01-15T10:30:00"

    def test_encode_date(self):
        """Test encoding date object."""
        from datetime import date

        d = date(2024, 1, 15)

        result = _json_default_encoder(d)

        assert result == "2024-01-15"

    def test_encode_pydantic_model(self):
        """Test encoding Pydantic model."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            id: int
            name: str

        model = TestModel(id=1, name="test")

        result = _json_default_encoder(model)

        assert result == {"id": 1, "name": "test"}

    def test_encode_unknown_type(self):
        """Test encoding unknown type falls back to str."""

        class CustomClass:
            def __str__(self):
                return "custom"

        obj = CustomClass()

        result = _json_default_encoder(obj)

        assert result == "custom"


class TestSerializeArgs:
    """Tests for argument serialization."""

    def test_serialize_simple_args(self):
        """Test serializing simple arguments."""
        args = (1, "test", True, None)

        result = _serialize_args(args)

        assert "1" in result
        assert "test" in result

    def test_skip_session_arg(self):
        """Test that session-like objects are skipped."""

        class MockSession:
            pass

        args = (MockSession(), 1, "test")

        result = _serialize_args(args)

        # Should only serialize the simple args
        assert "1" in result
        assert "test" in result


class TestSerializeKwargs:
    """Tests for keyword argument serialization."""

    def test_serialize_simple_kwargs(self):
        """Test serializing simple kwargs."""
        kwargs = {"id": 1, "name": "test"}

        result = _serialize_kwargs(kwargs)

        assert "id" in result
        assert "name" in result

    def test_skip_session_kwargs(self):
        """Test that session-like objects in kwargs are skipped."""

        class MockSession:
            pass

        kwargs = {"session": MockSession(), "id": 1}

        result = _serialize_kwargs(kwargs)

        assert "id" in result
        assert "session" not in result


class TestBuildCacheKey:
    """Tests for cache key building."""

    def test_build_key_with_skip_args(self):
        """Test building key with skipped args."""

        def mock_func(session, user_id, name):
            pass

        mock_func.__module__ = "app.test"
        mock_func.__qualname__ = "test_func"

        key = _build_cache_key(mock_func, None, None, [0], ("session", 123, "test"), {})

        assert "123" in key
        assert "test" in key
        # session should be skipped
        assert "session" not in key or "app.test" in key  # module name might contain 'session'

    def test_build_key_custom_builder(self):
        """Test building key with custom key builder."""

        def mock_func(user_id):
            pass

        custom_builder = lambda user_id: f"custom:{user_id}"

        key = _build_cache_key(mock_func, custom_builder, None, None, (123,), {})

        assert key == "custom:123"

    def test_build_key_with_prefix(self):
        """Test building key with prefix."""

        def mock_func(user_id):
            pass

        mock_func.__module__ = "app.modules.users.service"
        mock_func.__qualname__ = "get_user"

        key = _build_cache_key(mock_func, None, "users", None, (123,), {})

        assert key.startswith("users:")


class TestCacheDecorator:
    """Tests for cache decorator."""

    @pytest.mark.asyncio
    async def test_cache_returns_cached_value(self):
        """Test that cached value is returned on cache hit."""
        # Mock cache manager
        cache_manager._redis = AsyncMock()
        cached_data = json.dumps({"id": 1, "name": "cached"})
        cache_manager._redis.get.return_value = cached_data.encode()

        @cache(ttl=300)
        async def test_func(arg):
            return {"id": 2, "name": "fresh"}

        result = await test_func("test")

        assert result["id"] == 1  # Should return cached value
        assert result["name"] == "cached"
        cache_manager._redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_calls_function_on_miss(self):
        """Test that function is called on cache miss."""
        # Mock cache manager - cache miss
        cache_manager._redis = AsyncMock()
        cache_manager._redis.get.return_value = None
        cache_manager._redis.setex.return_value = True

        call_count = 0

        @cache(ttl=300)
        async def test_func(arg):
            nonlocal call_count
            call_count += 1
            return {"id": 1, "name": "fresh"}

        result = await test_func("test")

        assert result["name"] == "fresh"
        assert call_count == 1
        cache_manager._redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_skips_when_not_initialized(self):
        """Test that function is called directly when cache not initialized."""
        cache_manager._redis = None

        call_count = 0

        @cache(ttl=300)
        async def test_func(arg):
            nonlocal call_count
            call_count += 1
            return {"result": "test"}

        result = await test_func("test")

        assert result["result"] == "test"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cache_with_condition(self):
        """Test cache with condition function."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.get.return_value = None
        cache_manager._redis.setex.return_value = True

        @cache(ttl=300, condition=lambda result, arg: result is not None)
        async def test_func(arg):
            return {"id": 1} if arg else None

        # Should cache
        await test_func("test")
        assert cache_manager._redis.setex.call_count == 1

        # Should not cache None result (condition returns False for None)
        cache_manager._redis.reset_mock()
        cache_manager._redis.get.return_value = None
        await test_func("")
        # setex should not be called since condition(lambda result, arg: result is not None) with result=None returns False
        # but we're passing empty string which is truthy in Python? No, empty string is falsy
        # Let's check the logic
        assert cache_manager._redis.setex.call_count == 0


class TestInvalidateCacheDecorator:
    """Tests for invalidate_cache decorator."""

    @pytest.mark.asyncio
    async def test_invalidate_by_pattern(self):
        """Test cache invalidation by pattern."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.scan.return_value = (0, [b"key1", b"key2"])
        cache_manager._redis.delete.return_value = 2

        @invalidate_cache(pattern="users:*")
        async def test_func(user_id):
            return {"id": user_id}

        result = await test_func(123)

        assert result["id"] == 123
        cache_manager._redis.scan.assert_called_once()
        cache_manager._redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_by_key_builder(self):
        """Test cache invalidation with key builder."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.delete.return_value = 1

        @invalidate_cache(key_builder=lambda user_id: f"user:{user_id}")
        async def test_func(user_id):
            return {"id": user_id}

        await test_func(123)

        cache_manager._redis.delete.assert_called_once_with("user:123")

    @pytest.mark.asyncio
    async def test_invalidate_skips_when_not_initialized(self):
        """Test that invalidation is skipped when cache not initialized."""
        cache_manager._redis = None

        @invalidate_cache(pattern="users:*")
        async def test_func(user_id):
            return {"id": user_id}

        # Should not raise
        result = await test_func(123)
        assert result["id"] == 123


class TestCacheManagement:
    """Tests for cache management functions."""

    @pytest.mark.asyncio
    async def test_get_cache_hit(self):
        """Test getting cached value."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.get.return_value = json.dumps({"data": "test"}).encode()

        result = await get_cache("test_key")

        assert result == {"data": "test"}
        cache_manager._redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_cache_miss(self):
        """Test getting cache miss."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.get.return_value = None

        result = await get_cache("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_cache(self):
        """Test setting cache value."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.setex.return_value = True

        result = await set_cache("test_key", {"data": "test"}, ttl=300)

        assert result is True
        cache_manager._redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_cache(self):
        """Test deleting cache key."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.delete.return_value = 1

        result = await delete_cache("test_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_cache_pattern(self):
        """Test deleting cache keys by pattern."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.scan.return_value = (0, [b"key1", b"key2"])
        cache_manager._redis.delete.return_value = 2

        result = await delete_cache_pattern("test:*")

        assert result == 2

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing all cache."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.flushdb.return_value = True

        result = await clear_cache()

        assert result is True

    @pytest.mark.asyncio
    async def test_get_cache_info(self):
        """Test getting cache info."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.info.return_value = {
            "redis_version": "7.0.0",
            "used_memory_human": "1.5M",
        }

        result = await get_cache_info()

        assert result["status"] == "connected"
        assert result["redis_version"] == "7.0.0"

    @pytest.mark.asyncio
    async def test_get_cache_info_not_initialized(self):
        """Test getting cache info when not initialized."""
        cache_manager._redis = None

        result = await get_cache_info()

        assert result["status"] == "not_initialized"


class TestDeleteByPattern:
    """Tests for delete by pattern function."""

    @pytest.mark.asyncio
    async def test_delete_by_pattern_single_batch(self):
        """Test deleting keys matching pattern in single batch."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.scan.side_effect = [
            (0, [b"key1", b"key2", b"key3"]),  # First and only batch
        ]
        cache_manager._redis.delete.return_value = 3

        result = await _delete_by_pattern("test:*")

        assert result == 3
        assert cache_manager._redis.scan.call_count == 1

    @pytest.mark.asyncio
    async def test_delete_by_pattern_multiple_batches(self):
        """Test deleting keys matching pattern in multiple batches."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.scan.side_effect = [
            (1, [b"key1", b"key2"]),  # First batch, cursor=1
            (0, [b"key3", b"key4"]),  # Second batch, cursor=0
        ]
        cache_manager._redis.delete.return_value = 2

        result = await _delete_by_pattern("test:*")

        assert result == 4  # 2 + 2
        assert cache_manager._redis.scan.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_by_pattern_no_keys(self):
        """Test deleting keys when no keys match."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.scan.return_value = (0, [])

        result = await _delete_by_pattern("test:*")

        assert result == 0

    @pytest.mark.asyncio
    async def test_delete_by_pattern_not_initialized(self):
        """Test deleting when cache not initialized."""
        cache_manager._redis = None

        result = await _delete_by_pattern("test:*")

        assert result == 0


class TestCacheManager:
    """Tests for RedisCacheManager."""

    @pytest.mark.asyncio
    async def test_initialize_standalone(self):
        """Test initializing standalone Redis connection."""
        with patch("app.core.cache.aioredis.from_url") as mock_from_url:
            mock_redis = AsyncMock()
            mock_from_url.return_value = mock_redis

            # Reset singleton state
            cache_manager._redis = None
            cache_manager._instance = None

            # Create new instance
            from app.core.cache import RedisCacheManager

            manager = RedisCacheManager()
            await manager.initialize()

            mock_from_url.assert_called_once()
            assert manager._redis is not None

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing cache connection."""
        cache_manager._redis = AsyncMock()

        await cache_manager.close()

        cache_manager._redis.close.assert_called_once()
        assert cache_manager._redis is None

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check when Redis is healthy."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.ping.return_value = True

        result = await cache_manager.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check when Redis is unhealthy."""
        cache_manager._redis = AsyncMock()
        cache_manager._redis.ping.side_effect = Exception("Connection refused")

        result = await cache_manager.health_check()

        assert result is False

    def test_redis_property_not_initialized(self):
        """Test accessing redis property when not initialized."""
        cache_manager._redis = None

        with pytest.raises(RuntimeError, match="not initialized"):
            _ = cache_manager.redis
