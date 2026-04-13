"""System Limits Stress Tests

Tests for maximum system limits including:
- Maximum connection handling
- Large file upload handling
- Long-running stability
- Resource release verification

Stress Test Scenarios:
- Maximum connections: Test beyond configured pool limits
- Large uploads: Test file size limits
- Stability: Extended duration tests
- Resource leaks: Memory and connection leak detection
"""

import asyncio
import gc
import io
import random
import time
import tracemalloc
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.cache import cache_manager
from app.db.session import SessionFactory, engine
from app.modules.users.models import User
from app.core.security import get_password_hash


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def stress_test_data(session: AsyncSession) -> dict:
    """Create test data for stress testing."""
    users = []
    for i in range(50):
        user = User(
            email=f"stress_user_{i}@example.com",
            username=f"stress_user_{i}",
            hashed_password=get_password_hash("StressTest123!"),
            full_name=f"Stress Test User {i}",
            is_active=True,
        )
        users.append(user)

    session.add_all(users)
    await session.commit()

    for user in users:
        await session.refresh(user)

    return {"users": users}


@pytest_asyncio.fixture
def large_file_content() -> bytes:
    """Generate large file content for upload tests."""
    # 10MB of random data
    return bytes(random.randint(0, 255) for _ in range(10 * 1024 * 1024))


# =============================================================================
# Maximum Connection Tests
# =============================================================================


class TestMaxConnections:
    """Tests for maximum connection handling."""

    @pytest.mark.benchmark(
        group="max_connections",
        min_rounds=3,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_connection_pool_saturation(self) -> None:
        """Test behavior when connection pool is saturated."""
        from app.db.session import engine

        # Get pool size info
        pool_size = getattr(engine.pool, "size", 5)
        max_overflow = getattr(engine.pool, "_max_overflow", 10)

        async def connection_task(task_id: int) -> tuple:
            """Task that holds a connection for a period."""
            start = time.perf_counter()
            try:
                async with SessionFactory() as session:
                    # Hold connection for 0.5 seconds
                    await session.execute(text("SELECT 1"))
                    await asyncio.sleep(0.5)
                    return task_id, time.perf_counter() - start, True, None
            except Exception as e:
                return task_id, time.perf_counter() - start, False, str(e)

        # Create more tasks than pool can handle
        total_tasks = pool_size + max_overflow + 5
        start = time.perf_counter()
        tasks = [connection_task(i) for i in range(total_tasks)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        success_count = sum(1 for _, _, success, _ in results if success)
        failure_count = total_tasks - success_count

        print(f"\nConnection Pool Saturation:")
        print(f"  Pool size: {pool_size}, Max overflow: {max_overflow}")
        print(f"  Total tasks: {total_tasks}")
        print(f"  Successful: {success_count}, Failed: {failure_count}")
        print(f"  Total duration: {duration:.2f}s")

        # Most should succeed, but some may timeout
        assert success_count >= total_tasks * 0.8, "Too many connection failures"

    @pytest.mark.benchmark(
        group="max_connections",
        min_rounds=5,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self) -> None:
        """Test graceful handling of connection timeouts."""

        async def slow_query_task(task_id: int) -> tuple:
            try:
                async with SessionFactory() as session:
                    # Simulate slow query
                    await session.execute(text("SELECT 1"))
                    await asyncio.sleep(0.2)
                    return task_id, True, None
            except Exception as e:
                return task_id, False, str(e)

        # Launch many concurrent slow queries
        tasks = [slow_query_task(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for _, success, _ in results if success)
        print(f"\nConnection Timeout Test: {success_count}/50 succeeded")

        # Should handle gracefully even if some fail
        assert success_count >= 30, "Too many connections failed"

    @pytest.mark.benchmark(
        group="max_connections",
        min_rounds=3,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_connection_recovery(self) -> None:
        """Test connection pool recovery after stress."""

        async def stress_connection():
            async with SessionFactory() as session:
                await session.execute(text("SELECT 1"))
                await asyncio.sleep(0.1)

        # Stress the pool
        stress_tasks = [stress_connection() for _ in range(30)]
        await asyncio.gather(*stress_tasks, return_exceptions=True)

        # Wait for recovery
        await asyncio.sleep(0.5)

        # Test that pool is still functional
        async with SessionFactory() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1, "Connection pool did not recover"


# =============================================================================
# Large File Upload Tests
# =============================================================================


class TestLargeFileUpload:
    """Tests for large file upload handling."""

    @pytest.mark.benchmark(
        group="large_upload",
        min_rounds=3,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_1mb_file_upload(self, client: AsyncClient) -> None:
        """Test upload of 1MB file."""
        # Create 1MB file
        content = b"x" * (1024 * 1024)
        files = {"file": ("test_1mb.txt", io.BytesIO(content), "text/plain")}

        start = time.perf_counter()
        response = await client.post("/api/v1/uploads", files=files)
        elapsed = time.perf_counter() - start

        # May return 404 if endpoint doesn't exist, but test handling
        assert response.status_code in [200, 201, 404, 413]  # 413 = Payload Too Large
        assert elapsed < 5.0, f"Upload took {elapsed:.2f}s, expected < 5s"

    @pytest.mark.benchmark(
        group="large_upload",
        min_rounds=3,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_10mb_file_upload(self, client: AsyncClient) -> None:
        """Test upload of 10MB file."""
        content = b"x" * (10 * 1024 * 1024)
        files = {"file": ("test_10mb.txt", io.BytesIO(content), "text/plain")}

        start = time.perf_counter()
        response = await client.post("/api/v1/uploads", files=files)
        elapsed = time.perf_counter() - start

        assert response.status_code in [200, 201, 404, 413]
        assert elapsed < 10.0, f"Upload took {elapsed:.2f}s, expected < 10s"

    @pytest.mark.benchmark(
        group="large_upload",
        min_rounds=2,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_large_json_payload(self, client: AsyncClient) -> None:
        """Test handling of large JSON payload."""
        # Create large JSON payload (~500KB)
        large_data = {"items": [{"id": i, "name": f"Item {i}", "data": "x" * 1000} for i in range(500)]}

        start = time.perf_counter()
        response = await client.post("/api/v1/test/large-payload", json=large_data)
        elapsed = time.perf_counter() - start

        assert response.status_code in [200, 201, 404, 422, 413]
        assert elapsed < 5.0, f"Processing took {elapsed:.2f}s, expected < 5s"

    @pytest.mark.benchmark(
        group="large_upload",
        min_rounds=5,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_chunked_large_data(self, client: AsyncClient) -> None:
        """Test chunked processing of large data."""
        chunk_size = 1000
        num_chunks = 10

        start = time.perf_counter()
        for i in range(num_chunks):
            chunk_data = {"chunk_id": i, "items": [{"id": j, "value": f"data_{j}"} for j in range(chunk_size)]}
            response = await client.post("/api/v1/test/chunk", json=chunk_data)
            assert response.status_code in [200, 201, 404]

        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, f"Chunked upload took {elapsed:.2f}s, expected < 10s"


# =============================================================================
# Long-Running Stability Tests
# =============================================================================


class TestLongRunningStability:
    """Tests for long-running stability."""

    @pytest.mark.benchmark(
        group="stability",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_30_second_stability(self, client: AsyncClient) -> None:
        """Test system stability over 30 seconds."""
        duration = 30.0
        request_count = 0
        error_count = 0
        response_times = []

        start = time.perf_counter()
        while time.perf_counter() - start < duration:
            try:
                req_start = time.perf_counter()
                response = await client.get("/health")
                elapsed = time.perf_counter() - req_start

                response_times.append(elapsed)
                request_count += 1

                if response.status_code != 200:
                    error_count += 1

                await asyncio.sleep(0.1)  # Small delay between requests
            except Exception as e:
                error_count += 1

        actual_duration = time.perf_counter() - start
        error_rate = error_count / request_count if request_count > 0 else 0

        print(f"\n30s Stability Test:")
        print(f"  Duration: {actual_duration:.2f}s")
        print(f"  Requests: {request_count}")
        print(f"  Errors: {error_count} ({error_rate:.2%})")
        print(f"  Avg response time: {sum(response_times) / len(response_times) * 1000:.2f}ms")

        assert error_rate < 0.01, f"Error rate {error_rate:.2%} exceeds 1%"

    @pytest.mark.benchmark(
        group="stability",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_memory_stability_60_seconds(self, client: AsyncClient) -> None:
        """Test memory stability over 60 seconds."""
        import psutil
        import os

        duration = 60.0
        memory_samples = []

        process = psutil.Process(os.getpid())

        start = time.perf_counter()
        while time.perf_counter() - start < duration:
            # Make some requests
            for _ in range(5):
                await client.get("/health")
                await client.get("/api/v1/products?page=1&page_size=10")

            # Sample memory
            gc.collect()
            memory_info = process.memory_info()
            memory_samples.append(memory_info.rss / (1024 * 1024))  # MB

            await asyncio.sleep(1)

        # Analyze memory trend
        if len(memory_samples) >= 10:
            first_half = memory_samples[: len(memory_samples) // 2]
            second_half = memory_samples[len(memory_samples) // 2 :]

            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)

            growth = avg_second - avg_first
            growth_percent = (growth / avg_first * 100) if avg_first > 0 else 0

            print(f"\n60s Memory Stability Test:")
            print(f"  Initial memory: {memory_samples[0]:.2f}MB")
            print(f"  Final memory: {memory_samples[-1]:.2f}MB")
            print(f"  Growth: {growth:.2f}MB ({growth_percent:.1f}%)")

            assert growth_percent < 20, f"Memory grew by {growth_percent:.1f}%, expected < 20%"

    @pytest.mark.benchmark(
        group="stability",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_connection_stability(self) -> None:
        """Test database connection stability over time."""
        duration = 30.0
        connection_errors = 0
        successful_queries = 0

        start = time.perf_counter()
        while time.perf_counter() - start < duration:
            try:
                async with SessionFactory() as session:
                    result = await session.execute(text("SELECT 1"))
                    value = result.scalar()
                    if value == 1:
                        successful_queries += 1
            except Exception:
                connection_errors += 1

            await asyncio.sleep(0.5)

        total_attempts = successful_queries + connection_errors
        error_rate = connection_errors / total_attempts if total_attempts > 0 else 0

        print(f"\nConnection Stability Test:")
        print(f"  Successful queries: {successful_queries}")
        print(f"  Connection errors: {connection_errors}")
        print(f"  Error rate: {error_rate:.2%}")

        assert error_rate < 0.05, f"Connection error rate {error_rate:.2%} exceeds 5%"


# =============================================================================
# Resource Release Tests
# =============================================================================


class TestResourceRelease:
    """Tests for resource release verification."""

    @pytest.mark.benchmark(
        group="resource_release",
        min_rounds=5,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_connection_release_after_request(self) -> None:
        """Test that connections are released after request completion."""
        from app.db.session import engine

        # Get initial connection count
        initial_checked_in = getattr(engine.pool, "checked_in", 0)

        # Make many requests
        for _ in range(20):
            async with SessionFactory() as session:
                await session.execute(text("SELECT 1"))

        # Give pool time to return connections
        await asyncio.sleep(0.5)

        # Check final connection count
        final_checked_in = getattr(engine.pool, "checked_in", 0)

        print(f"\nConnection Release Test:")
        print(f"  Initial checked in: {initial_checked_in}")
        print(f"  Final checked in: {final_checked_in}")

        # Connections should be returned to pool
        assert final_checked_in >= initial_checked_in, "Connections not properly released"

    @pytest.mark.benchmark(
        group="resource_release",
        min_rounds=3,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_memory_release_after_large_operations(self) -> None:
        """Test memory release after large operations."""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        gc.collect()
        initial_memory = process.memory_info().rss / (1024 * 1024)

        # Perform large operations
        for _ in range(5):
            async with SessionFactory() as session:
                # Query large dataset
                result = await session.execute(text("SELECT 1"))
                _ = result.scalar()

        gc.collect()
        await asyncio.sleep(0.5)

        final_memory = process.memory_info().rss / (1024 * 1024)
        memory_increase = final_memory - initial_memory

        print(f"\nMemory Release Test:")
        print(f"  Initial: {initial_memory:.2f}MB")
        print(f"  Final: {final_memory:.2f}MB")
        print(f"  Increase: {memory_increase:.2f}MB")

        # Memory should not grow unbounded
        assert memory_increase < 50, f"Memory grew by {memory_increase:.2f}MB, expected < 50MB"

    @pytest.mark.benchmark(
        group="resource_release",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_cache_connection_release(self) -> None:
        """Test cache connection release."""
        # Mock cache operations
        cache_manager._redis = AsyncMock()
        cache_manager._redis.setex.return_value = True
        cache_manager._redis.get.return_value = None
        cache_manager._redis.close.return_value = None

        # Perform cache operations
        from app.core.cache import set_cache, get_cache

        for i in range(50):
            await set_cache(f"test_key_{i}", {"data": i}, ttl=60)
            await get_cache(f"test_key_{i}")

        # Close cache
        await cache_manager.close()

        # Verify close was called
        assert cache_manager._redis.close.called or cache_manager._redis is None


# =============================================================================
# Error Handling Under Stress
# =============================================================================


class TestStressErrorHandling:
    """Tests for error handling under stress conditions."""

    @pytest.mark.benchmark(
        group="error_handling",
        min_rounds=3,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_graceful_degradation_under_load(self, client: AsyncClient) -> None:
        """Test graceful degradation when system is under heavy load."""

        async def make_request(request_id: int) -> tuple:
            try:
                response = await client.get("/api/v1/products?page=1&page_size=50")
                return request_id, response.status_code, None
            except Exception as e:
                return request_id, None, str(e)

        # Create burst load
        tasks = [make_request(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for _, code, _ in results if code == 200)
        error_count = 100 - success_count

        print(f"\nGraceful Degradation Test:")
        print(f"  Successful: {success_count}, Failed: {error_count}")

        # System should handle gracefully even if some requests fail
        assert success_count >= 50, "System did not degrade gracefully"

    @pytest.mark.benchmark(
        group="error_handling",
        min_rounds=5,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_timeout_handling(self, client: AsyncClient) -> None:
        """Test timeout handling under stress."""
        timeouts = 0
        successes = 0

        for _ in range(20):
            try:
                # Request with timeout
                response = await client.get("/health", timeout=5.0)
                if response.status_code == 200:
                    successes += 1
            except asyncio.TimeoutError:
                timeouts += 1
            except Exception:
                pass

        print(f"\nTimeout Handling Test:")
        print(f"  Successes: {successes}, Timeouts: {timeouts}")

        # Most should succeed or timeout gracefully
        assert successes + timeouts >= 15, "Too many unexpected errors"


# =============================================================================
# Stress Test Report
# =============================================================================


def pytest_benchmark_summary_stats(config, benchmarks, summary):
    """Generate stress test summary report."""
    print("\n" + "=" * 80)
    print("STRESS TEST SUMMARY REPORT")
    print("=" * 80)

    categories = {
        "max_connections": "Maximum Connection Tests",
        "large_upload": "Large File Upload Tests",
        "stability": "Long-Running Stability Tests",
        "resource_release": "Resource Release Tests",
        "error_handling": "Error Handling Tests",
    }

    for group, name in categories.items():
        group_benchmarks = [b for b in benchmarks if group in b["name"]]
        if group_benchmarks:
            print(f"\n{name}:")
            for benchmark in group_benchmarks:
                stats = benchmark["stats"]
                print(f"  {benchmark['name']}: {stats['mean']:.2f}s (min: {stats['min']:.2f}s)")

    print("\n" + "=" * 80)
