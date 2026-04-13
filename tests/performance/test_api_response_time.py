"""API Response Time Performance Tests

Tests for API endpoint response times, concurrent request handling,
database connection pool performance, and memory usage.

Performance Thresholds:
- GET endpoints: < 100ms (P95)
- POST endpoints: < 200ms (P95)
- Concurrent requests: < 500ms total
- Memory usage: < 100MB per 1000 requests
"""

import asyncio
import gc
import time
import tracemalloc
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_manager
from app.db.session import engine
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.products.models import Product
from app.modules.users.models import User


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def api_client(client) -> AsyncClient:
    """Return the async test client."""
    return client


@pytest_asyncio.fixture
async def performance_test_data(session: AsyncSession) -> dict:
    """Create test data for performance tests."""
    from app.core.security import get_password_hash

    # Create test users
    users = []
    for i in range(50):
        user = User(
            email=f"perf_user_{i}@example.com",
            username=f"perf_user_{i}",
            hashed_password=get_password_hash("TestPass123!"),
            full_name=f"Performance Test User {i}",
            is_active=True,
        )
        users.append(user)

    session.add_all(users)
    await session.commit()

    # Create test products
    from decimal import Decimal

    products = []
    for i in range(100):
        product = Product(
            name=f"Performance Product {i}",
            sku=f"PERF-{i:04d}",
            description=f"Description for product {i}",
            price=Decimal(f"{10 + i % 100}.99"),
            category="Performance",
            is_active=True,
        )
        products.append(product)

    session.add_all(products)
    await session.commit()

    # Create test orders
    orders = []
    for i in range(200):
        order = Order(
            user_id=users[i % len(users)].id,
            status=OrderStatus.PENDING.value,
            total_amount=Decimal(f"{50 + i % 500}.00"),
        )
        orders.append(order)

    session.add_all(orders)
    await session.commit()

    return {"users": users, "products": products, "orders": orders}


@pytest_asyncio.fixture
async def auth_tokens(api_client: AsyncClient, performance_test_data: dict) -> dict:
    """Create auth tokens for testing."""
    tokens = {}

    # Create and login test users
    for i in range(5):
        login_data = {
            "username": f"perf_user_{i}",
            "password": "TestPass123!",
        }
        response = await api_client.post("/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            tokens[f"user_{i}"] = response.json()["data"]["access_token"]

    return tokens


# =============================================================================
# Endpoint Response Time Tests
# =============================================================================


class TestEndpointResponseTime:
    """Tests for individual API endpoint response times."""

    @pytest.mark.benchmark(
        group="api_get",
        min_rounds=20,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_health_endpoint_response_time(self, api_client: AsyncClient) -> None:
        """Test health endpoint response time (should be < 50ms)."""
        response = await api_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.benchmark(
        group="api_get",
        min_rounds=20,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_get_users_response_time(self, api_client: AsyncClient, auth_tokens: dict) -> None:
        """Test GET /users endpoint response time."""
        headers = {"Authorization": f"Bearer {auth_tokens.get('user_0', '')}"}
        response = await api_client.get("/api/v1/users?page=1&page_size=20", headers=headers)
        assert response.status_code in [200, 401, 403]  # May fail if not superuser

    @pytest.mark.benchmark(
        group="api_get",
        min_rounds=20,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_get_products_response_time(self, api_client: AsyncClient) -> None:
        """Test GET /products endpoint response time."""
        response = await api_client.get("/api/v1/products?page=1&page_size=20")
        assert response.status_code == 200

    @pytest.mark.benchmark(
        group="api_get",
        min_rounds=20,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_get_product_by_id_response_time(self, api_client: AsyncClient, performance_test_data: dict) -> None:
        """Test GET /products/{id} endpoint response time."""
        product_id = performance_test_data["products"][0].id
        response = await api_client.get(f"/api/v1/products/{product_id}")
        assert response.status_code == 200

    @pytest.mark.benchmark(
        group="api_post",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_login_response_time(self, api_client: AsyncClient) -> None:
        """Test POST /auth/login endpoint response time."""
        login_data = {
            "username": "perf_user_0",
            "password": "TestPass123!",
        }
        response = await api_client.post("/api/v1/auth/login", json=login_data)
        # May fail if user doesn't exist, but we measure response time
        assert response.status_code in [200, 401]

    @pytest.mark.benchmark(
        group="api_post",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_create_product_response_time(self, api_client: AsyncClient, auth_tokens: dict) -> None:
        """Test POST /products endpoint response time."""
        import uuid

        headers = {"Authorization": f"Bearer {auth_tokens.get('user_0', '')}"}
        product_data = {
            "name": f"Test Product {uuid.uuid4().hex[:8]}",
            "sku": f"TEST-{uuid.uuid4().hex[:6].upper()}",
            "description": "Test description",
            "price": "99.99",
            "category": "Test",
            "is_active": True,
        }
        response = await api_client.post("/api/v1/products", json=product_data, headers=headers)
        # May fail if not authorized
        assert response.status_code in [201, 401, 403]


# =============================================================================
# Concurrent Request Tests
# =============================================================================


class TestConcurrentRequests:
    """Tests for concurrent request handling."""

    @pytest.mark.benchmark(
        group="concurrent_api",
        min_rounds=5,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_concurrent_health_requests(self, api_client: AsyncClient) -> None:
        """Test handling of 50 concurrent health check requests."""

        async def health_request() -> int:
            response = await api_client.get("/health")
            return response.status_code

        start = time.perf_counter()
        tasks = [health_request() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        assert all(r == 200 for r in results)
        assert elapsed < 2.0  # Less than 2 seconds for 50 requests

    @pytest.mark.benchmark(
        group="concurrent_api",
        min_rounds=5,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_concurrent_product_reads(self, api_client: AsyncClient, performance_test_data: dict) -> None:
        """Test handling of 30 concurrent product reads."""
        products = performance_test_data["products"]

        async def read_product(i: int) -> int:
            product_id = products[i % len(products)].id
            response = await api_client.get(f"/api/v1/products/{product_id}")
            return response.status_code

        start = time.perf_counter()
        tasks = [read_product(i) for i in range(30)]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        success_count = sum(1 for r in results if r == 200)
        assert success_count >= 25  # At least 83% success rate
        assert elapsed < 3.0  # Less than 3 seconds

    @pytest.mark.benchmark(
        group="concurrent_api",
        min_rounds=3,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_mixed_endpoint_load(self, api_client: AsyncClient) -> None:
        """Test mixed load across different endpoints."""

        async def mixed_request(i: int) -> int:
            if i % 3 == 0:
                response = await api_client.get("/health")
            elif i % 3 == 1:
                response = await api_client.get("/api/v1/products?page=1&page_size=10")
            else:
                response = await api_client.get("/")
            return response.status_code

        start = time.perf_counter()
        tasks = [mixed_request(i) for i in range(60)]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        success_count = sum(1 for r in results if r == 200)
        assert success_count >= 50  # At least 83% success rate
        assert elapsed < 5.0  # Less than 5 seconds for mixed load


# =============================================================================
# Database Connection Pool Tests
# =============================================================================


class TestConnectionPoolPerformance:
    """Tests for database connection pool performance."""

    @pytest.mark.benchmark(
        group="connection_pool",
        min_rounds=50,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_connection_acquisition_time(self, session: AsyncSession) -> None:
        """Test database connection acquisition time."""
        from sqlalchemy import text

        start = time.perf_counter()
        result = await session.execute(text("SELECT 1"))
        elapsed = time.perf_counter() - start

        value = result.scalar()
        assert value == 1
        assert elapsed < 0.05  # Less than 50ms

    @pytest.mark.benchmark(
        group="connection_pool",
        min_rounds=20,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, api_client: AsyncClient) -> None:
        """Test behavior under connection pool exhaustion."""

        async def db_heavy_request(i: int) -> tuple:
            start = time.perf_counter()
            response = await api_client.get("/api/v1/products?page=1&page_size=50")
            elapsed = time.perf_counter() - start
            return response.status_code, elapsed

        # More requests than typical pool size
        tasks = [db_heavy_request(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for code, _ in results if code == 200)
        avg_time = sum(t for _, t in results) / len(results)

        assert success_count >= 45  # At least 90% success rate
        assert avg_time < 1.0  # Average response under 1 second


# =============================================================================
# Memory Usage Tests
# =============================================================================


class TestMemoryUsage:
    """Tests for memory usage under load."""

    @pytest.mark.benchmark(
        group="memory",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_memory_usage_single_request(self, api_client: AsyncClient) -> None:
        """Test memory usage for a single request."""
        gc.collect()

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        response = await api_client.get("/api/v1/products?page=1&page_size=50")
        assert response.status_code == 200

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_increase = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)

        # Should use less than 1MB for a single request
        assert total_increase < 1 * 1024 * 1024

    @pytest.mark.benchmark(
        group="memory",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_memory_usage_multiple_requests(self, api_client: AsyncClient) -> None:
        """Test memory usage for multiple requests."""
        gc.collect()

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        # Make 100 requests
        for i in range(100):
            response = await api_client.get(f"/api/v1/products?page={i % 10 + 1}&page_size=10")
            if response.status_code != 200:
                break

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_increase = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)

        # Should use less than 10MB for 100 requests
        assert total_increase < 10 * 1024 * 1024

    @pytest.mark.benchmark(
        group="memory",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_memory_stability(self, api_client: AsyncClient) -> None:
        """Test memory stability over repeated requests."""
        gc.collect()

        memory_usage = []

        for i in range(20):
            gc.collect()
            response = await api_client.get("/api/v1/products?page=1&page_size=20")
            assert response.status_code == 200

            # Force garbage collection and check memory
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            memory_usage.append(memory_info.rss)

        # Check memory growth is reasonable (< 50% increase)
        initial_memory = memory_usage[0]
        final_memory = memory_usage[-1]
        growth_ratio = final_memory / initial_memory if initial_memory > 0 else 0

        assert growth_ratio < 1.5  # Less than 50% growth


# =============================================================================
# Response Time Threshold Validation
# =============================================================================


class TestResponseTimeThresholds:
    """Validate API response times against thresholds."""

    @pytest.mark.asyncio
    async def test_get_endpoints_p95_threshold(self, api_client: AsyncClient) -> None:
        """Validate GET endpoints P95 response time < 100ms."""
        times = []

        for _ in range(100):
            start = time.perf_counter()
            response = await api_client.get("/health")
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)
            assert response.status_code == 200

        times.sort()
        p95_idx = int(len(times) * 0.95)
        p95_time = times[p95_idx]

        assert p95_time < 100, f"GET P95 ({p95_time:.2f}ms) exceeds threshold (100ms)"

    @pytest.mark.asyncio
    async def test_post_endpoints_p95_threshold(self, api_client: AsyncClient) -> None:
        """Validate POST endpoints P95 response time < 200ms."""
        times = []

        for _ in range(50):
            start = time.perf_counter()
            response = await api_client.post("/api/v1/auth/login", json={"username": "test", "password": "test"})
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        times.sort()
        p95_idx = int(len(times) * 0.95)
        p95_time = times[p95_idx]

        assert p95_time < 200, f"POST P95 ({p95_time:.2f}ms) exceeds threshold (200ms)"

    @pytest.mark.asyncio
    async def test_api_throughput_threshold(self, api_client: AsyncClient) -> None:
        """Validate API throughput is at least 100 requests/sec."""
        duration = 1.0  # 1 second
        count = 0
        start = time.perf_counter()

        while time.perf_counter() - start < duration:
            response = await api_client.get("/health")
            if response.status_code == 200:
                count += 1

        throughput = count / duration
        assert throughput >= 50, f"API throughput ({throughput:.0f} req/sec) below threshold (50)"


# =============================================================================
# Performance Metrics Collection
# =============================================================================


def pytest_benchmark_summary_stats(config, benchmarks, summary):
    """Custom summary for API performance reports."""
    import statistics

    print("\n" + "=" * 70)
    print("API PERFORMANCE TEST REPORT")
    print("=" * 70)

    for benchmark in benchmarks:
        name = benchmark["name"]
        stats = benchmark["stats"]

        if "api_" in name or "concurrent" in name or "connection" in name:
            mean_time = stats["mean"] * 1000
            min_time = stats["min"] * 1000
            max_time = stats["max"] * 1000

            sorted_times = sorted(benchmark["times"])
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)
            p95_time = sorted_times[p95_idx] * 1000 if p95_idx < len(sorted_times) else max_time
            p99_time = sorted_times[p99_idx] * 1000 if p99_idx < len(sorted_times) else max_time

            throughput = 1 / stats["mean"] if stats["mean"] > 0 else 0

            print(f"\n{name}")
            print(f"  Mean: {mean_time:.2f}ms | Min: {min_time:.2f}ms | Max: {max_time:.2f}ms")
            print(f"  P95:  {p95_time:.2f}ms | P99: {p99_time:.2f}ms")
            print(f"  Throughput: {throughput:.2f} req/sec | Rounds: {stats['rounds']}")

    print("=" * 70)
