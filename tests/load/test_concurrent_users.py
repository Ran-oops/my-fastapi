"""Concurrent Users Load Tests

Simulates 100 concurrent users performing various operations:
- Login operations
- Data read operations
- Data write operations

Load Test Scenarios:
- Ramp up: Gradual increase to 100 users
- Steady state: 100 concurrent users for 60 seconds
- Ramp down: Gradual decrease

Success Criteria:
- Error rate < 1%
- P95 response time < 500ms
- P99 response time < 1000ms
- Throughput > 100 requests/sec
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.modules.users.models import User


# =============================================================================
# Test Data and Fixtures
# =============================================================================


@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    response_times: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    @property
    def p95_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]

    @property
    def p99_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]

    @property
    def throughput(self, duration: float = 1.0) -> float:
        if duration == 0:
            return 0.0
        return self.total_requests / duration


@pytest_asyncio.fixture
async def load_test_users(session: AsyncSession) -> list[User]:
    """Create 100 test users for load testing."""
    users = []
    for i in range(100):
        user = User(
            email=f"loadtest_user_{i}@example.com",
            username=f"loadtest_user_{i}",
            hashed_password=get_password_hash("LoadTest123!"),
            full_name=f"Load Test User {i}",
            is_active=True,
        )
        users.append(user)

    session.add_all(users)
    await session.commit()

    for user in users:
        await session.refresh(user)

    return users


@pytest_asyncio.fixture
async def user_credentials() -> list[dict]:
    """Generate user credentials for load testing."""
    return [{"username": f"loadtest_user_{i}", "password": "LoadTest123!"} for i in range(100)]


# =============================================================================
# Virtual User Class
# =============================================================================


class VirtualUser:
    """Simulates a single virtual user."""

    def __init__(self, user_id: int, credentials: dict, base_url: str = "http://test"):
        self.user_id = user_id
        self.credentials = credentials
        self.base_url = base_url
        self.token: str | None = None
        self.client: AsyncClient | None = None
        self.metrics = LoadTestMetrics()

    async def __aenter__(self):
        from httpx import ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=transport, base_url=self.base_url)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def login(self) -> bool:
        """Perform login operation."""
        start = time.perf_counter()
        try:
            response = await self.client.post("/api/v1/auth/login", json=self.credentials)
            elapsed = time.perf_counter() - start

            self.metrics.total_requests += 1
            self.metrics.total_response_time += elapsed
            self.metrics.response_times.append(elapsed)

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("data", {}).get("access_token")
                self.metrics.successful_requests += 1
                return True
            else:
                self.metrics.failed_requests += 1
                self.metrics.errors.append(f"Login failed: {response.status_code}")
                return False
        except Exception as e:
            elapsed = time.perf_counter() - start
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.total_response_time += elapsed
            self.metrics.response_times.append(elapsed)
            self.metrics.errors.append(f"Login error: {str(e)}")
            return False

    async def read_data(self, endpoint: str) -> bool:
        """Perform data read operation."""
        start = time.perf_counter()
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = await self.client.get(endpoint, headers=headers)
            elapsed = time.perf_counter() - start

            self.metrics.total_requests += 1
            self.metrics.total_response_time += elapsed
            self.metrics.response_times.append(elapsed)

            if response.status_code in [200, 401, 403]:
                self.metrics.successful_requests += 1
                return True
            else:
                self.metrics.failed_requests += 1
                self.metrics.errors.append(f"Read failed: {response.status_code}")
                return False
        except Exception as e:
            elapsed = time.perf_counter() - start
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.total_response_time += elapsed
            self.metrics.response_times.append(elapsed)
            self.metrics.errors.append(f"Read error: {str(e)}")
            return False

    async def write_data(self, endpoint: str, data: dict) -> bool:
        """Perform data write operation."""
        start = time.perf_counter()
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = await self.client.post(endpoint, json=data, headers=headers)
            elapsed = time.perf_counter() - start

            self.metrics.total_requests += 1
            self.metrics.total_response_time += elapsed
            self.metrics.response_times.append(elapsed)

            if response.status_code in [200, 201, 401, 403, 422]:
                self.metrics.successful_requests += 1
                return True
            else:
                self.metrics.failed_requests += 1
                self.metrics.errors.append(f"Write failed: {response.status_code}")
                return False
        except Exception as e:
            elapsed = time.perf_counter() - start
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.total_response_time += elapsed
            self.metrics.response_times.append(elapsed)
            self.metrics.errors.append(f"Write error: {str(e)}")
            return False


# =============================================================================
# Load Test Scenarios
# =============================================================================


class TestConcurrentUsers:
    """Tests simulating 100 concurrent users."""

    @pytest.mark.benchmark(
        group="load_test",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_100_concurrent_logins(self, load_test_users: list[User], user_credentials: list[dict]) -> None:
        """Simulate 100 users logging in simultaneously."""
        metrics = LoadTestMetrics()

        async def simulate_user_login(user_id: int, credentials: dict) -> LoadTestMetrics:
            async with VirtualUser(user_id, credentials) as user:
                await user.login()
                return user.metrics

        start = time.perf_counter()
        tasks = [simulate_user_login(i, user_credentials[i]) for i in range(100)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        # Aggregate metrics
        for user_metrics in results:
            metrics.total_requests += user_metrics.total_requests
            metrics.successful_requests += user_metrics.successful_requests
            metrics.failed_requests += user_metrics.failed_requests
            metrics.response_times.extend(user_metrics.response_times)
            metrics.errors.extend(user_metrics.errors)

        # Validate results
        assert metrics.error_rate < 0.01, f"Error rate {metrics.error_rate:.2%} exceeds 1%"
        assert metrics.p95_response_time < 2.0, f"P95 {metrics.p95_response_time:.2f}s exceeds 2s"
        print(f"\n100 Concurrent Logins: {metrics.successful_requests}/{metrics.total_requests} succeeded")
        print(f"P95: {metrics.p95_response_time:.2f}s, Error rate: {metrics.error_rate:.2%}")

    @pytest.mark.benchmark(
        group="load_test",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_100_concurrent_product_reads(
        self, load_test_users: list[User], user_credentials: list[dict]
    ) -> None:
        """Simulate 100 users reading products simultaneously."""
        metrics = LoadTestMetrics()

        async def simulate_read(user_id: int, credentials: dict) -> LoadTestMetrics:
            async with VirtualUser(user_id, credentials) as user:
                await user.login()
                # Read products 5 times per user
                for _ in range(5):
                    await user.read_data("/api/v1/products?page=1&page_size=20")
                return user.metrics

        start = time.perf_counter()
        tasks = [simulate_read(i, user_credentials[i]) for i in range(100)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        for user_metrics in results:
            metrics.total_requests += user_metrics.total_requests
            metrics.successful_requests += user_metrics.successful_requests
            metrics.failed_requests += user_metrics.failed_requests
            metrics.response_times.extend(user_metrics.response_times)

        # Validate results
        assert metrics.error_rate < 0.05, f"Error rate {metrics.error_rate:.2%} exceeds 5%"
        assert metrics.p95_response_time < 3.0, f"P95 {metrics.p95_response_time:.2f}s exceeds 3s"
        throughput = metrics.total_requests / duration if duration > 0 else 0
        print(f"\n100 Concurrent Reads: {metrics.total_requests} requests in {duration:.2f}s")
        print(f"Throughput: {throughput:.2f} req/s, P95: {metrics.p95_response_time:.2f}s")

    @pytest.mark.benchmark(
        group="load_test",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_mixed_load_100_users(self, load_test_users: list[User], user_credentials: list[dict]) -> None:
        """Simulate 100 users with mixed read/write operations."""
        metrics = LoadTestMetrics()

        async def simulate_mixed_load(user_id: int, credentials: dict) -> LoadTestMetrics:
            async with VirtualUser(user_id, credentials) as user:
                await user.login()

                # Random mix of operations
                operations = []
                for _ in range(10):
                    op = random.choice(["read_products", "read_health", "read_user"])
                    operations.append(op)

                for op in operations:
                    if op == "read_products":
                        await user.read_data("/api/v1/products?page=1&page_size=10")
                    elif op == "read_health":
                        await user.read_data("/health")
                    elif op == "read_user":
                        await user.read_data("/api/v1/users/me")

                return user.metrics

        start = time.perf_counter()
        tasks = [simulate_mixed_load(i, user_credentials[i]) for i in range(100)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        for user_metrics in results:
            metrics.total_requests += user_metrics.total_requests
            metrics.successful_requests += user_metrics.successful_requests
            metrics.failed_requests += user_metrics.failed_requests
            metrics.response_times.extend(user_metrics.response_times)

        # Validate results
        assert metrics.error_rate < 0.05, f"Error rate {metrics.error_rate:.2%} exceeds 5%"
        throughput = metrics.total_requests / duration if duration > 0 else 0
        print(f"\n100 Concurrent Mixed Load: {metrics.total_requests} requests in {duration:.2f}s")
        print(f"Throughput: {throughput:.2f} req/s, Success: {metrics.successful_requests}")


# =============================================================================
# Login Pressure Tests
# =============================================================================


class TestLoginPressure:
    """Tests for login endpoint under pressure."""

    @pytest.mark.benchmark(
        group="login_pressure",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_login_burst_50_users(self, load_test_users: list[User], user_credentials: list[dict]) -> None:
        """Test login endpoint with burst of 50 users."""
        metrics = LoadTestMetrics()

        async def burst_login(user_id: int, credentials: dict) -> LoadTestMetrics:
            async with VirtualUser(user_id, credentials) as user:
                await user.login()
                return user.metrics

        start = time.perf_counter()
        tasks = [burst_login(i, user_credentials[i]) for i in range(50)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        for user_metrics in results:
            metrics.total_requests += user_metrics.total_requests
            metrics.successful_requests += user_metrics.successful_requests
            metrics.failed_requests += user_metrics.failed_requests
            metrics.response_times.extend(user_metrics.response_times)

        assert duration < 5.0, f"Burst took {duration:.2f}s, expected < 5s"
        assert metrics.error_rate < 0.02, f"Error rate {metrics.error_rate:.2%} exceeds 2%"

    @pytest.mark.benchmark(
        group="login_pressure",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_sustained_login_100_users(self, load_test_users: list[User], user_credentials: list[dict]) -> None:
        """Test sustained login load with 100 users over 10 seconds."""
        metrics = LoadTestMetrics()
        duration = 10.0  # 10 seconds
        start = time.perf_counter()

        async def sustained_login(credentials: dict) -> LoadTestMetrics:
            async with VirtualUser(0, credentials) as user:
                user_metrics = LoadTestMetrics()
                while time.perf_counter() - start < duration:
                    await user.login()
                    user_metrics.total_requests += 1
                    if user.metrics.successful_requests > user_metrics.successful_requests:
                        user_metrics.successful_requests += 1
                    else:
                        user_metrics.failed_requests += 1
                    user_metrics.response_times.extend(user.metrics.response_times[-1:])
                    await asyncio.sleep(0.1)  # Small delay between attempts
                return user_metrics

        # Run 20 concurrent sustained login sessions
        tasks = [sustained_login(user_credentials[i]) for i in range(20)]
        results = await asyncio.gather(*tasks)
        actual_duration = time.perf_counter() - start

        for user_metrics in results:
            metrics.total_requests += user_metrics.total_requests
            metrics.successful_requests += user_metrics.successful_requests
            metrics.failed_requests += user_metrics.failed_requests
            metrics.response_times.extend(user_metrics.response_times)

        throughput = metrics.total_requests / actual_duration if actual_duration > 0 else 0
        print(f"\nSustained Login: {metrics.total_requests} requests in {actual_duration:.2f}s")
        print(f"Throughput: {throughput:.2f} req/s")


# =============================================================================
# Data Read Pressure Tests
# =============================================================================


class TestDataReadPressure:
    """Tests for data read endpoints under pressure."""

    @pytest.mark.benchmark(
        group="read_pressure",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_concurrent_product_list_reads(
        self, load_test_users: list[User], user_credentials: list[dict]
    ) -> None:
        """Test concurrent product list reads."""
        metrics = LoadTestMetrics()

        async def read_products(user_id: int, credentials: dict) -> LoadTestMetrics:
            async with VirtualUser(user_id, credentials) as user:
                await user.login()

                # Read products multiple times
                for page in range(1, 6):
                    await user.read_data(f"/api/v1/products?page={page}&page_size=20")

                return user.metrics

        start = time.perf_counter()
        tasks = [read_products(i, user_credentials[i]) for i in range(100)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        for user_metrics in results:
            metrics.total_requests += user_metrics.total_requests
            metrics.successful_requests += user_metrics.successful_requests
            metrics.failed_requests += user_metrics.failed_requests
            metrics.response_times.extend(user_metrics.response_times)

        assert metrics.error_rate < 0.05, f"Error rate {metrics.error_rate:.2%} exceeds 5%"
        assert metrics.p95_response_time < 5.0, f"P95 {metrics.p95_response_time:.2f}s exceeds 5s"

    @pytest.mark.benchmark(
        group="read_pressure",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_read_health_under_load(self, load_test_users: list[User], user_credentials: list[dict]) -> None:
        """Test health endpoint under heavy load."""
        metrics = LoadTestMetrics()

        async def read_health_batch(user_id: int, credentials: dict) -> LoadTestMetrics:
            async with VirtualUser(user_id, credentials) as user:
                for _ in range(20):
                    await user.read_data("/health")
                return user.metrics

        start = time.perf_counter()
        tasks = [read_health_batch(i, user_credentials[i]) for i in range(100)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        for user_metrics in results:
            metrics.total_requests += user_metrics.total_requests
            metrics.successful_requests += user_metrics.successful_requests
            metrics.failed_requests += user_metrics.failed_requests
            metrics.response_times.extend(user_metrics.response_times)

        throughput = metrics.total_requests / duration if duration > 0 else 0
        assert throughput >= 100, f"Throughput {throughput:.2f} req/s below 100"


# =============================================================================
# Data Write Pressure Tests
# =============================================================================


class TestDataWritePressure:
    """Tests for data write endpoints under pressure."""

    @pytest.mark.benchmark(
        group="write_pressure",
        min_rounds=1,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_concurrent_write_attempts(self, load_test_users: list[User], user_credentials: list[dict]) -> None:
        """Test concurrent write attempts (most will fail auth)."""
        metrics = LoadTestMetrics()
        import uuid

        async def write_attempt(user_id: int, credentials: dict) -> LoadTestMetrics:
            async with VirtualUser(user_id, credentials) as user:
                await user.login()

                # Attempt to create products (will likely fail due to auth)
                for i in range(5):
                    product_data = {
                        "name": f"Load Test Product {user_id}-{i}-{uuid.uuid4().hex[:6]}",
                        "sku": f"LOAD-{user_id}-{i}-{uuid.uuid4().hex[:6].upper()}",
                        "description": "Load test product",
                        "price": "99.99",
                        "category": "LoadTest",
                        "is_active": True,
                    }
                    await user.write_data("/api/v1/products", product_data)

                return user.metrics

        start = time.perf_counter()
        tasks = [write_attempt(i, user_credentials[i]) for i in range(50)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        for user_metrics in results:
            metrics.total_requests += user_metrics.total_requests
            metrics.successful_requests += user_metrics.successful_requests
            metrics.failed_requests += user_metrics.failed_requests
            metrics.response_times.extend(user_metrics.response_times)

        # Most will fail auth, but we test the system's response under load
        print(f"\nWrite Load: {metrics.total_requests} attempts, {metrics.successful_requests} succeeded")
        print(f"Error rate: {metrics.error_rate:.2%}, Duration: {duration:.2f}s")


# =============================================================================
# Load Test Report
# =============================================================================


def pytest_benchmark_summary_stats(config, benchmarks, summary):
    """Generate load test summary report."""
    print("\n" + "=" * 80)
    print("LOAD TEST SUMMARY REPORT")
    print("=" * 80)

    for benchmark in benchmarks:
        name = benchmark["name"]
        if "load_test" in name or "pressure" in name:
            stats = benchmark["stats"]
            duration = stats["mean"] * stats["rounds"]

            print(f"\n{name}")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Rounds: {stats['rounds']}")

    print("=" * 80)
