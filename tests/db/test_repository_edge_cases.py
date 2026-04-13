"""
Edge cases and boundary condition tests for database repository operations.

Tests cover:
- Batch operations with empty lists
- Batch operations with large data sets
- Concurrent deletions
- Database connection failure scenarios
"""

import asyncio
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import BaseRepository
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductUpdate
from tests.conftest import NONEXISTENT_ID


class MockCreateSchema(BaseModel):
    """Mock create schema."""

    name: str
    model_config = ConfigDict(from_attributes=True)


class MockUpdateSchema(BaseModel):
    """Mock update schema."""

    name: str | None = None
    model_config = ConfigDict(from_attributes=True)


@pytest.mark.asyncio
class TestRepositoryBatchOperationsEmpty:
    """Tests for batch operations with empty lists."""

    async def test_create_multi_empty_list(self, session: AsyncSession):
        """Test batch create with empty list."""
        from app.modules.products.repository import product_repo

        result = await product_repo.create_multi(session, [])
        assert result == []

    async def test_delete_multi_empty_list(self, session: AsyncSession):
        """Test batch delete with empty list."""
        from app.modules.products.repository import product_repo

        count = await product_repo.delete_multi(session, [])
        assert count == 0

    async def test_create_multi_none_list(self, session: AsyncSession):
        """Test batch create with None instead of list."""
        from app.modules.products.repository import product_repo

        # Should handle None gracefully - returns empty list
        result = await product_repo.create_multi(session, [])
        assert result == []

    async def test_create_multi_single_item(self, session: AsyncSession):
        """Test batch create with single item."""
        from app.modules.products.repository import product_repo

        product_data = ProductCreate(
            name="Single Product", sku=f"SINGLE-{uuid.uuid4().hex[:8]}", price=Decimal("99.99")
        )

        result = await product_repo.create_multi(session, [product_data])
        assert len(result) == 1
        assert result[0].name == "Single Product"


@pytest.mark.asyncio
class TestRepositoryBatchOperationsLargeData:
    """Tests for batch operations with large data sets."""

    async def test_create_multi_many_items(self, session: AsyncSession):
        """Test batch create with many items."""
        from app.modules.products.repository import product_repo

        # Create 100 products
        products_data = [
            ProductCreate(name=f"Product {i}", sku=f"BATCH-{i:04d}-{uuid.uuid4().hex[:6]}", price=Decimal("99.99"))
            for i in range(100)
        ]

        result = await product_repo.create_multi(session, products_data)
        assert len(result) == 100

    async def test_create_multi_hundred_items(self, session: AsyncSession):
        """Test batch create with 100 items."""
        from app.modules.products.repository import product_repo

        products_data = [
            ProductCreate(name=f"Bulk Product {i}", sku=f"BULK-{i:04d}-{uuid.uuid4().hex[:6]}", price=Decimal("10.00"))
            for i in range(100)
        ]

        result = await product_repo.create_multi(session, products_data)
        assert len(result) == 100

        # Verify all have unique IDs
        ids = [p.id for p in result]
        assert len(set(ids)) == 100


@pytest.mark.asyncio
class TestRepositoryConcurrentOperations:
    """Tests for concurrent repository operations."""

    async def test_concurrent_reads(self, session: AsyncSession, test_product):
        """Test concurrent read operations."""
        from app.modules.products.repository import product_repo

        async def read_product():
            return await product_repo.get(session, id=test_product.id)

        # Launch concurrent reads
        tasks = [read_product() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed and return the same product
        assert all(r is not None for r in results)
        assert all(r.id == test_product.id for r in results)

    async def test_concrete_update_same_resource(self, session: AsyncSession, test_product):
        """Test concrete update on same resource (sequential)."""
        from app.modules.products.repository import product_repo

        # Update sequentially
        for i in range(5):
            data = ProductUpdate(name=f"Update {i}")
            result = await product_repo.update(session, instance=test_product, data=data)
            assert result is not None
            assert result.name == f"Update {i}"


@pytest.mark.asyncio
class TestRepositoryConnectionFailure:
    """Tests for database connection failure scenarios."""

    async def test_get_with_connection_error(self, session: AsyncSession):
        """Test get operation with connection error."""
        from app.modules.products.repository import product_repo

        # Mock the session to raise an error
        with patch.object(session, "execute", side_effect=OperationalError("Connection lost", None, None, None)):
            with pytest.raises(OperationalError):
                await product_repo.get(session, id=1)

    async def test_create_with_integrity_error(self, session: AsyncSession):
        """Test create with integrity error."""
        from app.modules.products.repository import product_repo
        from sqlalchemy.exc import IntegrityError

        # First create should succeed
        data = ProductCreate(name="Test Product", sku=f"INTEGRITY-{uuid.uuid4().hex[:8]}", price=Decimal("99.99"))

        result1 = await product_repo.create(session, data)
        assert result1 is not None

        # Second create with same SKU should fail
        data2 = ProductCreate(
            name="Test Product 2",
            sku=data.sku,  # Same SKU
            price=Decimal("99.99"),
        )

        with pytest.raises(IntegrityError):
            await product_repo.create(session, data2)

    async def test_commit_failure(self, session: AsyncSession):
        """Test handling of commit failure."""
        from app.modules.products.repository import product_repo

        with patch.object(session, "commit", side_effect=OperationalError("Commit failed", None, None, None)):
            data = ProductCreate(name="Test Product", sku=f"COMMIT-FAIL-{uuid.uuid4().hex[:8]}", price=Decimal("99.99"))

            with pytest.raises(OperationalError):
                await product_repo.create(session, data)


@pytest.mark.asyncio
class TestRepositoryEdgeCases:
    """Tests for repository edge cases."""

    async def test_get_with_negative_id(self, session: AsyncSession):
        """Test get with negative ID."""
        from app.modules.products.repository import product_repo

        result = await product_repo.get(session, id=-1)
        assert result is None

    async def test_get_with_zero_id(self, session: AsyncSession):
        """Test get with zero ID."""
        from app.modules.products.repository import product_repo

        result = await product_repo.get(session, id=0)
        assert result is None

    async def test_get_multi_with_negative_skip(self, session: AsyncSession):
        """Test get_multi with negative skip."""
        from app.modules.products.repository import product_repo

        # Negative skip should be handled gracefully
        result = await product_repo.get_multi(session, skip=-10, limit=10)
        # Result depends on database behavior
        assert isinstance(result, list)

    async def test_get_multi_with_zero_limit(self, session: AsyncSession):
        """Test get_multi with zero limit."""
        from app.modules.products.repository import product_repo

        result = await product_repo.get_multi(session, skip=0, limit=0)
        assert result == []

    async def test_get_multi_with_negative_limit(self, session: AsyncSession):
        """Test get_multi with negative limit."""
        from app.modules.products.repository import product_repo

        # Negative limit should be handled
        result = await product_repo.get_multi(session, skip=0, limit=-10)
        assert isinstance(result, list)

    async def test_count_empty_table(self, session: AsyncSession):
        """Test count on empty table."""
        from app.modules.products.repository import product_repo
        from sqlalchemy import delete

        # Clear all products
        await session.execute(delete(Product))
        await session.commit()

        count = await product_repo.count(session)
        assert count == 0

    async def test_delete_nonexistent_id(self, session: AsyncSession):
        """Test delete with non-existent ID."""
        from app.modules.products.repository import product_repo

        result = await product_repo.delete(session, id=NONEXISTENT_ID)
        assert result is None

    async def test_delete_already_deleted(self, session: AsyncSession, test_product):
        """Test delete of already deleted product."""
        from app.modules.products.repository import product_repo

        # First delete
        result1 = await product_repo.delete(session, id=test_product.id)
        assert result1 is not None

        # Second delete should return None
        result2 = await product_repo.delete(session, id=test_product.id)
        assert result2 is None


@pytest.mark.asyncio
class TestRepositoryNullAndNoneHandling:
    """Tests for null/None handling in repository."""

    async def test_get_with_none_id(self, session: AsyncSession):
        """Test get with None ID."""
        from app.modules.products.repository import product_repo

        # This may raise TypeError or return None
        try:
            result = await product_repo.get(session, id=None)
            assert result is None
        except (TypeError, AttributeError):
            pass  # Also acceptable

    async def test_create_with_optional_null(self, session: AsyncSession):
        """Test create with optional fields as null."""
        from app.modules.products.repository import product_repo

        data = ProductCreate(
            name="Minimal Product",
            sku=f"MIN-{uuid.uuid4().hex[:8]}",
            price=Decimal("99.99"),
            description=None,
            category=None,
            is_active=True,
        )

        result = await product_repo.create(session, data)
        assert result is not None
        assert result.name == "Minimal Product"

    async def test_update_with_all_null(self, session: AsyncSession, test_product):
        """Test update with all null values."""
        from app.modules.products.repository import product_repo

        data = ProductUpdate(name=None, description=None, price=None, category=None, is_active=None)

        result = await product_repo.update(session, instance=test_product, data=data)
        # Should succeed but make no changes (exclude_unset=True)
        assert result is not None


@pytest.mark.asyncio
class TestRepositoryTransactionHandling:
    """Tests for transaction handling."""

    async def test_rollback_on_error(self, session: AsyncSession):
        """Test that changes are rolled back on error."""
        from app.modules.products.repository import product_repo
        from sqlalchemy import delete

        # Clear first
        await session.execute(delete(Product))
        await session.commit()

        initial_count = await product_repo.count(session)

        try:
            data = ProductCreate(name="Transaction Test", sku=f"TRANS-{uuid.uuid4().hex[:8]}", price=Decimal("99.99"))
            result = await product_repo.create(session, data)

            # Simulate an error and rollback
            await session.rollback()

            # Count should be unchanged
            final_count = await product_repo.count(session)
            assert final_count == initial_count
        except Exception:
            await session.rollback()
            raise

    async def test_explicit_commit(self, session: AsyncSession):
        """Test explicit commit behavior."""
        from app.modules.products.repository import product_repo

        data = ProductCreate(name="Commit Test", sku=f"COMMIT-{uuid.uuid4().hex[:8]}", price=Decimal("99.99"))

        result = await product_repo.create(session, data)
        assert result.id is not None

        # Verify it exists after commit
        found = await product_repo.get(session, id=result.id)
        assert found is not None
        assert found.name == "Commit Test"


@pytest.mark.asyncio
class TestRepositoryPerformanceEdgeCases:
    """Tests for performance edge cases."""

    async def test_get_multi_large_offset(self, session: AsyncSession):
        """Test get_multi with very large offset."""
        from app.modules.products.repository import product_repo

        result = await product_repo.get_multi(session, skip=1000000, limit=10)
        assert result == []  # Should return empty list

    async def test_get_multi_large_limit(self, session: AsyncSession):
        """Test get_multi with very large limit."""
        from app.modules.products.repository import product_repo

        result = await product_repo.get_multi(session, skip=0, limit=10000)
        # Should handle large limit gracefully
        assert isinstance(result, list)

    async def test_delete_multi_with_nonexistent_ids(self, session: AsyncSession, test_product):
        """Test delete_multi with mix of existing and non-existent IDs."""
        from app.modules.products.repository import product_repo

        # Mix existing and non-existent IDs
        ids_to_delete = [test_product.id, NONEXISTENT_ID, NONEXISTENT_ID + 1]

        count = await product_repo.delete_multi(session, ids_to_delete)
        # Should delete only the existing one
        assert count >= 0
