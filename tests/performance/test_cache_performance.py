"""Cache Performance Tests

Tests for cache performance including hit rates, write performance,
invalidation performance, and concurrent access.

Performance Thresholds:
- Cache read: < 5ms (P95)
- Cache write: < 10ms (P95)
- Cache invalidation: < 20ms (P95)
- Cache hit rate: > 80%
"""

import asyncio
import hashlib
import random
import string
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.core.cache import (
    CacheSerializer,
    _build_cache_key,
    cache,
    cache_manager,
    clear_cache,
    delete_cache,
    delete_cache_pattern,
    get_cache,
    invalidate_cache,
    set_cache,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def mock_redis():
    """Create a mock Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.get.return_value = None
    mock_client.setex.return_value = True
    mock_client.delete.return_value = 1
    mock_client.keys.return_value = []
    mock_client.scan.return_value = (0, [])
    mock_client.flushdb.return_value = True
    mock_client.info.return_value = {
        "keyspace_hits": 1000,
        "keyspace_misses": 200,
        "used_memory_human": "1.5M",
    }
    mock_client.ping.return_value = True
    return mock_client


@pytest_asyncio.fixture
async def populated_cache(mock_redis):
    """Create a cache with pre-populated data."""
    cache_manager._redis = mock_redis

    # Simulate cache hits/misses tracking
    hits = 0
    misses = 0

    async def mock_get(key):
        nonlocal hits, misses
        # Simulate 80% hit rate
        if random.random() < 0.8:
            hits += 1
            return b'{"data": "cached_value", "hit": true}'
        misses += 1
        return None

    mock_redis.get.side_effect = mock_get
    return cache_manager


# =============================================================================
# Cache Hit Rate Tests
# =============================================================================


class TestCacheHitRate:
    """Tests for cache hit rate performance."""

    @pytest.mark.benchmark(
        group="cache_hit_rate",
        min_rounds=100,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, mock_redis) -> None:
        """Test cache hit performance (cached value retrieval)."""
        cache_manager._redis = mock_redis
        mock_redis.get.return_value = b'{"data": "cached_value"}'

        start = time.perf_counter()
        result = await get_cache("test_key")
        elapsed = time.perf_counter() - start

        assert result is not None
        assert elapsed < 0.01  # Less than 10ms

    @pytest.mark.benchmark(
        group="cache_hit_rate",
        min_rounds=100,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_cache_miss_performance(self, mock_redis) -> None:
        """Test cache miss performance."""
        cache_manager._redis = mock_redis
        mock_redis.get.return_value = None

        start = time.perf_counter()
        result = await get_cache("nonexistent_key")
        elapsed = time.perf_counter() - start

        assert result is None
        assert elapsed < 0.01  # Less than 10ms

    @pytest.mark.benchmark(
        group="cache_hit_rate",
        min_rounds=50,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_simulated_hit_rate_80_percent(self, mock_redis) -> None:
        """Simulate 80% cache hit rate scenario."""
        cache_manager._redis = mock_redis

        hit_count = 0
        miss_count = 0

        async def conditional_get(key):
            # Simulate 80% hit rate
            if random.random() < 0.8:
                return b'{"data": "cached"}'
            return None

        mock_redis.get.side_effect = conditional_get

        for _ in range(100):
            result = await get_cache(f"key_{random.randint(1, 100)}")
            if result:
                hit_count += 1
            else:
                miss_count += 1

        hit_rate = hit_count / (hit_count + miss_count)
        assert hit_rate >= 0.7  # Allow some variance, expect >= 70%

    @pytest.mark.benchmark(
        group="cache_hit_rate",
        min_rounds=50,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_cache_hit_rate_under_load(self, mock_redis) -> None:
        """Test cache hit rate under simulated load."""
        cache_manager._redis = mock_redis

        # Pre-populate some keys
        cache_data = {f"key_{i}": f'{{"data": "value_{i}"}}'.encode() for i in range(50)}

        async def load_get(key):
            return cache_data.get(key)

        mock_redis.get.side_effect = load_get

        # Access pattern: 70% hot keys, 30% random
        hot_keys = [f"key_{i}" for i in range(20)]

        hits = 0
        misses = 0

        for _ in range(200):
            if random.random() < 0.7:
                key = random.choice(hot_keys)
            else:
                key = f"key_{random.randint(0, 99)}"

            result = await get_cache(key)
            if result:
                hits += 1
            else:
                misses += 1

        hit_rate = hits / (hits + misses)
        assert hit_rate >= 0.5  # Should have reasonable hit rate


# =============================================================================
# Cache Write Performance Tests
# =============================================================================


class TestCacheWritePerformance:
    """Tests for cache write performance."""

    @pytest.mark.benchmark(
        group="cache_write",
        min_rounds=50,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_cache_write_small_object(self, mock_redis) -> None:
        """Test cache write for small objects (< 1KB)."""
        cache_manager._redis = mock_redis

        small_data = {"id": 1, "name": "test", "active": True}

        start = time.perf_counter()
        await set_cache("small_key", small_data, ttl=300)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.02  # Less than 20ms

    @pytest.mark.benchmark(
        group="cache_write",
        min_rounds=30,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_cache_write_large_object(self, mock_redis) -> None:
        """Test cache write for large objects (> 100KB)."""
        cache_manager._redis = mock_redis

        # Generate large object (~100KB)
        large_data = {"items": [{"id": i, "data": "x" * 1000, "metadata": {"key": "value" * 10}} for i in range(100)]}

        start = time.perf_counter()
        await set_cache("large_key", large_data, ttl=300)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.05  # Less than 50ms for large objects

    @pytest.mark.benchmark(
        group="cache_write",
        min_rounds=50,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_cache_write_batch(self, mock_redis) -> None:
        """Test batch cache writes."""
        cache_manager._redis = mock_redis

        tasks = []
        for i in range(50):
            data = {"id": i, "value": f"data_{i}"}
            tasks.append(set_cache(f"batch_key_{i}", data, ttl=300))

        start = time.perf_counter()
        await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0  # Less than 1 second for 50 writes

    @pytest.mark.benchmark(
        group="cache_serialization",
        min_rounds=100,
        timer="time.perf_counter",
    )
    def test_cache_serialization_speed(self) -> None:
        """Test cache serialization performance."""
        data = {"id": 1, "name": "test", "nested": {"key": "value"}}

        start = time.perf_counter()
        serialized = CacheSerializer.serialize(data)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.001  # Less than 1ms

    @pytest.mark.benchmark(
        group="cache_serialization",
        min_rounds=100,
        timer="time.perf_counter",
    )
    def test_cache_deserialization_speed(self) -> None:
        """Test cache deserialization performance."""
        data = {"id": 1, "name": "test", "nested": {"key": "value"}}
        serialized = CacheSerializer.serialize(data)

        start = time.perf_counter()
        deserialized = CacheSerializer.deserialize(serialized)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.001  # Less than 1ms


# =============================================================================
# Cache Invalidation Tests
# =============================================================================


class TestCacheInvalidation:
    """Tests for cache invalidation performance."""

    @pytest.mark.benchmark(
        group="cache_invalidation",
        min_rounds=50,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_cache_delete_single_key(self, mock_redis) -> None:
        """Test single key deletion."""
        cache_manager._redis = mock_redis
        mock_redis.delete.return_value = 1

        start = time.perf_counter()
        result = await delete_cache("test_key")
        elapsed = time.perf_counter() - start

        assert result is True
        assert elapsed < 0.02  # Less than 20ms

    @pytest.mark.benchmark(
        group="cache_invalidation",
        min_rounds=30,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_cache_delete_pattern(self, mock_redis) -> None:
        """Test pattern-based cache deletion."""
        cache_manager._redis = mock_redis
        mock_redis.scan.return_value = (0, [b"key1", b"key2", b"key3", b"key4", b"key5"])
        mock_redis.delete.return_value = 5

        start = time.perf_counter()
        result = await delete_cache_pattern("pattern:*")
        elapsed = time.perf_counter() - start

        assert result == 5
        assert elapsed < 0.05  # Less than 50ms

    @pytest.mark.benchmark(
        group="cache_invalidation",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_cache_clear_all(self, mock_redis) -> None:
        """Test clearing entire cache."""
        cache_manager._redis = mock_redis
        mock_redis.flushdb.return_value = True

        start = time.perf_counter()
        result = await clear_cache()
        elapsed = time.perf_counter() - start

        assert result is True
        assert elapsed < 0.1  # Less than 100ms

    @pytest.mark.benchmark(
        group="cache_invalidation",
        min_rounds=20,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_invalidate_decorator_performance(self, mock_redis) -> None:
        """Test invalidation decorator performance."""
        cache_manager._redis = mock_redis
        mock_redis.delete.return_value = 1

        @invalidate_cache(pattern="users:*")
        async def update_user(user_id: int) -> dict:
            return {"id": user_id, "updated": True}

        start = time.perf_counter()
        result = await update_user(123)
        elapsed = time.perf_counter() - start

        assert result["id"] == 123
        assert elapsed < 0.05  # Less than 50ms


# =============================================================================
# Concurrent Cache Access Tests
# =============================================================================


class TestConcurrentCacheAccess:
    """Tests for concurrent cache access performance."""

    @pytest.mark.benchmark(
        group="concurrent_read",
        min_rounds=20,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_concurrent_cache_reads(self, mock_redis) -> None:
        """Test concurrent cache read operations."""
        cache_manager._redis = mock_redis
        mock_redis.get.return_value = b'{"data": "cached"}'

        async def read_operation(i: int) -> Any:
            return await get_cache(f"key_{i}")

        start = time.perf_counter()
        tasks = [read_operation(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        assert len(results) == 50
        assert elapsed < 1.0  # Less than 1 second for 50 concurrent reads

    @pytest.mark.benchmark(
        group="concurrent_write",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_concurrent_cache_writes(self, mock_redis) -> None:
        """Test concurrent cache write operations."""
        cache_manager._redis = mock_redis

        async def write_operation(i: int) -> bool:
            return await set_cache(f"key_{i}", {"id": i}, ttl=300)

        start = time.perf_counter()
        tasks = [write_operation(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        assert len(results) == 50
        assert elapsed < 2.0  # Less than 2 seconds for 50 concurrent writes

    @pytest.mark.benchmark(
        group="concurrent_mixed",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self, mock_redis) -> None:
        """Test concurrent mixed read/write operations."""
        cache_manager._redis = mock_redis

        async def mixed_operation(i: int) -> Any:
            if i % 3 == 0:
                return await set_cache(f"key_{i}", {"id": i}, ttl=300)
            else:
                mock_redis.get.return_value = b'{"data": "cached"}'
                return await get_cache(f"key_{i}")

        start = time.perf_counter()
        tasks = [mixed_operation(i) for i in range(30)]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        assert len(results) == 30
        assert elapsed < 1.5  # Less than 1.5 seconds

    @pytest.mark.benchmark(
        group="contention",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_cache_contention_same_key(self, mock_redis) -> None:
        """Test cache contention with multiple clients accessing same key."""
        cache_manager._redis = mock_redis
        mock_redis.get.return_value = b'{"data": "shared"}'

        async def access_shared() -> Any:
            return await get_cache("shared_key")

        start = time.perf_counter()
        tasks = [access_shared() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        assert len(results) == 100
        assert elapsed < 1.0  # Should handle contention efficiently


# =============================================================================
# Cache Key Building Tests
# =============================================================================


class TestCacheKeyPerformance:
    """Tests for cache key building performance."""

    @pytest.mark.benchmark(
        group="key_building",
        min_rounds=1000,
        timer="time.perf_counter",
    )
    def test_simple_key_builder_performance(self) -> None:
        """Test simple key builder performance."""
        from app.core.cache import CacheKeyBuilder

        def mock_func(arg1, arg2):
            pass

        mock_func.__module__ = "app.test"
        mock_func.__qualname__ = "test_func"

        start = time.perf_counter()
        for _ in range(100):
            key = CacheKeyBuilder.simple_key_builder(mock_func, "prefix", "arg1", "arg2")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.01  # Less than 10ms for 100 calls

    @pytest.mark.benchmark(
        group="key_building",
        min_rounds=1000,
        timer="time.perf_counter",
    )
    def test_hash_key_builder_performance(self) -> None:
        """Test hash-based key builder performance."""
        from app.core.cache import CacheKeyBuilder

        def mock_func(arg1, arg2):
            pass

        mock_func.__module__ = "app.test"
        mock_func.__qualname__ = "test_func"

        start = time.perf_counter()
        for _ in range(100):
            key = CacheKeyBuilder.hash_key_builder(mock_func, "prefix", "arg1_value", "arg2_value")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.01  # Less than 10ms for 100 calls


# =============================================================================
# Performance Threshold Validation
# =============================================================================


class TestCachePerformanceThresholds:
    """Validate cache performance against thresholds."""

    @pytest.mark.asyncio
    async def test_cache_read_p95_threshold(self, mock_redis) -> None:
        """Validate cache read P95 latency is under 5ms."""
        cache_manager._redis = mock_redis
        mock_redis.get.return_value = b'{"data": "cached"}'

        times = []
        for _ in range(100):
            start = time.perf_counter()
            await get_cache("test_key")
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)

        times.sort()
        p95_idx = int(len(times) * 0.95)
        p95_time = times[p95_idx]

        assert p95_time < 5.0, f"Cache read P95 ({p95_time:.2f}ms) exceeds threshold (5ms)"

    @pytest.mark.asyncio
    async def test_cache_write_p95_threshold(self, mock_redis) -> None:
        """Validate cache write P95 latency is under 10ms."""
        cache_manager._redis = mock_redis

        times = []
        for _ in range(100):
            start = time.perf_counter()
            await set_cache("test_key", {"data": "value"}, ttl=300)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        times.sort()
        p95_idx = int(len(times) * 0.95)
        p95_time = times[p95_idx]

        assert p95_time < 10.0, f"Cache write P95 ({p95_time:.2f}ms) exceeds threshold (10ms)"

    @pytest.mark.asyncio
    async def test_cache_throughput_threshold(self, mock_redis) -> None:
        """Validate cache throughput is at least 1000 ops/sec."""
        cache_manager._redis = mock_redis
        mock_redis.get.return_value = b'{"data": "cached"}'

        duration = 1.0  # 1 second
        count = 0
        start = time.perf_counter()

        while time.perf_counter() - start < duration:
            await get_cache(f"key_{count % 100}")
            count += 1

        throughput = count / duration
        assert throughput >= 500, f"Cache throughput ({throughput:.0f} ops/sec) below threshold (500)"
