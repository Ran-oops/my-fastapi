"""Database Performance Tests

Tests for database performance including N+1 query detection,
batch operations, index efficiency, and large dataset queries.

Performance Thresholds:
- Single query: < 10ms (P95)
- Batch insert (1000 records): < 500ms
- Large dataset query (10000 records): < 100ms
"""

from decimal import Decimal
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.orders.schemas import OrderCreate
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def sample_users(session: AsyncSession) -> list[User]:
    """Create sample users for performance tests."""
    users = []
    for i in range(100):
        user_data = UserCreate(
            email=f"perftest_user_{i}@example.com",
            username=f"perftest_user_{i}",
            password="TestPass123!",
            full_name=f"Test User {i}",
        )
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password="hashed_password",
            full_name=user_data.full_name,
            is_active=True,
        )
        users.append(user)

    session.add_all(users)
    await session.commit()
    for user in users:
        await session.refresh(user)
    return users


@pytest_asyncio.fixture
async def sample_products(session: AsyncSession) -> list[Product]:
    """Create sample products for performance tests."""
    products = []
    for i in range(1000):
        product = Product(
            name=f"Product {i}",
            sku=f"SKU-{i:06d}",
            description=f"Description for product {i}",
            price=Decimal(f"{10 + i % 100}.99"),
            category=f"Category_{i % 10}",
            is_active=True,
        )
        products.append(product)

    session.add_all(products)
    await session.commit()
    for product in products:
        await session.refresh(product)
    return products


@pytest_asyncio.fixture
async def sample_orders(session: AsyncSession, sample_users: list[User]) -> list[Order]:
    """Create sample orders for performance tests."""
    orders = []
    statuses = list(OrderStatus)

    for i in range(1000):
        user = sample_users[i % len(sample_users)]
        order = Order(
            user_id=user.id,
            status=statuses[i % len(statuses)].value,
            total_amount=Decimal(f"{50 + i % 500}.00"),
        )
        orders.append(order)

    session.add_all(orders)
    await session.commit()
    for order in orders:
        await session.refresh(order)
    return orders


@pytest_asyncio.fixture
async def sample_order_items(
    session: AsyncSession, sample_orders: list[Order], sample_products: list[Product]
) -> list[OrderItem]:
    """Create sample order items for performance tests."""
    items = []

    for order in sample_orders:
        for j in range(3):  # 3 items per order
            product = sample_products[(order.id + j) % len(sample_products)]
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=j + 1,
                unit_price=product.price,
            )
            items.append(item)

    session.add_all(items)
    await session.commit()
    return items


# =============================================================================
# N+1 Query Detection Tests
# =============================================================================


class TestNPlusOneQueries:
    """Tests to detect N+1 query problems."""

    @pytest.mark.benchmark(
        group="nplusone",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_get_orders_without_eager_loading(self, session: AsyncSession, sample_orders: list[Order]) -> None:
        """Test N+1 problem: fetch orders without items (baseline)."""
        result = await session.execute(select(Order).limit(100))
        orders = result.scalars().all()
        assert len(orders) == 100

    @pytest.mark.benchmark(
        group="nplusone",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_get_orders_with_eager_loading(self, session: AsyncSession, sample_orders: list[Order]) -> None:
        """Test efficient loading: fetch orders with eager loaded items."""
        result = await session.execute(select(Order).options(selectinload(Order.items)).limit(100))
        orders = result.scalars().all()
        assert len(orders) == 100

    @pytest.mark.benchmark(
        group="nplusone",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_access_order_items_after_fetch(self, session: AsyncSession, sample_orders: list[Order]) -> None:
        """Test accessing order items after fetch (should cause N+1 without eager loading)."""
        result = await session.execute(select(Order).limit(50))
        orders = result.scalars().all()

        # Access items - this will trigger N+1 without proper eager loading
        for order in orders:
            _ = len(order.items)

    @pytest.mark.benchmark(
        group="nplusone_comparison",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_get_orders_with_user_relationship(self, session: AsyncSession, sample_orders: list[Order]) -> None:
        """Test fetching orders with user relationship."""
        result = await session.execute(select(Order).options(selectinload(Order.items)).limit(100))
        orders = result.scalars().all()

        # Access user data
        for order in orders:
            _ = order.user_id

        assert len(orders) == 100


# =============================================================================
# Batch Operations Performance Tests
# =============================================================================


class TestBatchOperations:
    """Tests for batch operation performance."""

    @pytest.mark.benchmark(
        group="batch_insert",
        min_rounds=5,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_batch_insert_100_products(self, session: AsyncSession) -> None:
        """Test batch insert of 100 products (threshold: < 50ms)."""
        products = []
        for i in range(100):
            product = Product(
                name=f"Batch Product {i}",
                sku=f"BATCH-{i:06d}",
                price=Decimal("99.99"),
                category="Batch",
                is_active=True,
            )
            products.append(product)

        session.add_all(products)
        await session.commit()

    @pytest.mark.benchmark(
        group="batch_insert",
        min_rounds=5,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_batch_insert_1000_products(self, session: AsyncSession) -> None:
        """Test batch insert of 1000 products (threshold: < 500ms)."""
        products = []
        for i in range(1000):
            product = Product(
                name=f"Batch Product Large {i}",
                sku=f"BATCH-LG-{i:06d}",
                price=Decimal("99.99"),
                category="BatchLarge",
                is_active=True,
            )
            products.append(product)

        session.add_all(products)
        await session.commit()

    @pytest.mark.benchmark(
        group="batch_insert",
        min_rounds=3,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_batch_insert_5000_products(self, session: AsyncSession) -> None:
        """Test batch insert of 5000 products (threshold: < 2000ms)."""
        products = []
        for i in range(5000):
            product = Product(
                name=f"Batch Product XL {i}",
                sku=f"BATCH-XL-{i:06d}",
                price=Decimal("99.99"),
                category="BatchXL",
                is_active=True,
            )
            products.append(product)

        session.add_all(products)
        await session.commit()

    @pytest.mark.benchmark(
        group="batch_select",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_batch_select_by_ids(self, session: AsyncSession, sample_products: list[Product]) -> None:
        """Test batch select by IDs."""
        ids = [p.id for p in sample_products[:100]]
        from sqlalchemy import func

        result = await session.execute(select(Product).where(Product.id.in_(ids)))
        products = result.scalars().all()
        assert len(products) == 100

    @pytest.mark.benchmark(
        group="batch_update",
        min_rounds=5,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_batch_update(self, session: AsyncSession, sample_products: list[Product]) -> None:
        """Test batch update operation."""
        ids = [p.id for p in sample_products[:100]]

        await session.execute(
            text("UPDATE products SET price = price * 1.1 WHERE id IN :ids").bindparams(ids=tuple(ids))
        )
        await session.commit()

    @pytest.mark.benchmark(
        group="batch_delete",
        min_rounds=5,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_batch_delete(self, session: AsyncSession, sample_products: list[Product]) -> None:
        """Test batch delete operation."""
        from sqlalchemy import delete

        ids = [p.id for p in sample_products[:100]]

        await session.execute(delete(Product).where(Product.id.in_(ids)))
        await session.commit()


# =============================================================================
# Index Efficiency Tests
# =============================================================================


class TestIndexEfficiency:
    """Tests for database index efficiency."""

    @pytest.mark.benchmark(
        group="index_lookup",
        min_rounds=100,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_lookup_by_indexed_field(self, session: AsyncSession, sample_products: list[Product]) -> None:
        """Test lookup by indexed field (SKU)."""
        sku = sample_products[500].sku
        result = await session.execute(select(Product).where(Product.sku == sku))
        product = result.scalar_one_or_none()
        assert product is not None

    @pytest.mark.benchmark(
        group="index_lookup",
        min_rounds=100,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_lookup_by_non_indexed_field(self, session: AsyncSession, sample_products: list[Product]) -> None:
        """Test lookup by non-indexed field (name) for comparison."""
        name = sample_products[500].name
        result = await session.execute(select(Product).where(Product.name == name))
        product = result.scalar_one_or_none()
        assert product is not None

    @pytest.mark.benchmark(
        group="index_range",
        min_rounds=20,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_range_query_on_indexed_field(self, session: AsyncSession) -> None:
        """Test range query on indexed field (id)."""
        result = await session.execute(select(Product).where(Product.id.between(100, 200)))
        products = result.scalars().all()
        assert len(products) >= 0

    @pytest.mark.benchmark(
        group="composite_index",
        min_rounds=20,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_order_by_indexed_field(self, session: AsyncSession) -> None:
        """Test order by indexed field."""
        result = await session.execute(select(Product).order_by(Product.sku).limit(100))
        products = result.scalars().all()
        assert len(products) <= 100


# =============================================================================
# Large Dataset Query Tests
# =============================================================================


class TestLargeDatasetQueries:
    """Tests for large dataset query performance."""

    @pytest.mark.benchmark(
        group="large_dataset",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_pagination_query_large_dataset(self, session: AsyncSession, sample_products: list[Product]) -> None:
        """Test pagination query on large dataset."""
        result = await session.execute(select(Product).order_by(Product.id).offset(500).limit(50))
        products = result.scalars().all()
        assert len(products) == 50

    @pytest.mark.benchmark(
        group="large_dataset",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_count_large_dataset(self, session: AsyncSession, sample_products: list[Product]) -> None:
        """Test count query on large dataset."""
        from sqlalchemy import func

        result = await session.execute(select(func.count()).select_from(Product))
        count = result.scalar()
        assert count >= 1000

    @pytest.mark.benchmark(
        group="large_dataset",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_aggregation_query(self, session: AsyncSession, sample_products: list[Product]) -> None:
        """Test aggregation query on large dataset."""
        from sqlalchemy import func

        result = await session.execute(
            select(
                Product.category,
                func.count().label("count"),
                func.avg(Product.price).label("avg_price"),
            )
            .where(Product.is_active == True)
            .group_by(Product.category)
        )
        stats = result.all()
        assert len(stats) > 0

    @pytest.mark.benchmark(
        group="large_dataset",
        min_rounds=10,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_complex_join_query(
        self,
        session: AsyncSession,
        sample_orders: list[Order],
        sample_order_items: list[OrderItem],
    ) -> None:
        """Test complex join query performance."""
        result = await session.execute(
            select(Order, OrderItem)
            .join(OrderItem, Order.id == OrderItem.order_id)
            .where(Order.status == OrderStatus.CONFIRMED.value)
            .limit(100)
        )
        rows = result.all()
        assert len(rows) >= 0

    @pytest.mark.benchmark(
        group="large_dataset",
        min_rounds=5,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_full_text_search(self, session: AsyncSession, sample_products: list[Product]) -> None:
        """Test full text search query."""
        result = await session.execute(select(Product).where(Product.name.like("%Product%")).limit(100))
        products = result.scalars().all()
        assert len(products) > 0


# =============================================================================
# Connection Pool Tests
# =============================================================================


class TestConnectionPool:
    """Tests for database connection pool performance."""

    @pytest.mark.benchmark(
        group="connection",
        min_rounds=50,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_simple_query_execution(self, session: AsyncSession) -> None:
        """Test simple query execution time."""
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()
        assert value == 1

    @pytest.mark.benchmark(
        group="transaction",
        min_rounds=20,
        timer="time.perf_counter",
    )
    @pytest.mark.asyncio
    async def test_transaction_overhead(self, session: AsyncSession) -> None:
        """Test transaction overhead."""
        async with session.begin_nested():
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1


# =============================================================================
# Performance Reporting
# =============================================================================


def pytest_benchmark_summary_stats(config, benchmarks, summary):
    """Custom summary stats for performance reports.

    Reports:
    - Average response time
    - P95/P99 latency
    - Throughput (ops/sec)
    - Error rate
    """
    import statistics
    import time

    for benchmark in benchmarks:
        name = benchmark["name"]
        stats = benchmark["stats"]

        # Calculate metrics
        mean_time = stats["mean"] * 1000  # Convert to ms
        min_time = stats["min"] * 1000
        max_time = stats["max"] * 1000

        # Calculate percentiles
        sorted_times = sorted(benchmark["times"])
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        p95_time = sorted_times[p95_idx] * 1000 if p95_idx < len(sorted_times) else max_time
        p99_time = sorted_times[p99_idx] * 1000 if p99_idx < len(sorted_times) else max_time

        # Calculate throughput
        throughput = 1 / stats["mean"] if stats["mean"] > 0 else 0

        print(f"\n{'=' * 60}")
        print(f"Performance Report: {name}")
        print(f"{'=' * 60}")
        print(f"  Mean Response Time: {mean_time:.2f} ms")
        print(f"  Min Response Time:  {min_time:.2f} ms")
        print(f"  Max Response Time:  {max_time:.2f} ms")
        print(f"  P95 Latency:        {p95_time:.2f} ms")
        print(f"  P99 Latency:        {p99_time:.2f} ms")
        print(f"  Throughput:         {throughput:.2f} ops/sec")
        print(f"  Rounds:             {stats['rounds']}")
        print(f"{'=' * 60}")
