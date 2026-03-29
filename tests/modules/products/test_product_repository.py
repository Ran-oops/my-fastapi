import uuid
from decimal import Decimal

import pytest

from app.modules.products.repository import product_repo
from app.modules.products.schemas import ProductCreate
from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestProductRepositoryGetBySku:
    async def test_get_by_sku_found(self, session, test_product):
        result = await product_repo.get_by_sku(session, sku=test_product.sku)
        assert result is not None
        assert result.sku == test_product.sku

    async def test_get_by_sku_not_found(self, session):
        result = await product_repo.get_by_sku(session, sku="NONEXISTENT")
        assert result is None


@pytest.mark.asyncio
class TestProductRepositoryGetByCategory:
    async def test_get_by_category_returns_matching(self, session, multiple_products):
        products = await product_repo.get_by_category(session, category="electronics")
        assert len(products) >= 2
        assert all(p.category == "electronics" for p in products)

    async def test_get_by_category_empty(self, session, multiple_products):
        products = await product_repo.get_by_category(session, category="nonexistent")
        assert len(products) == 0


@pytest.mark.asyncio
class TestProductRepositoryGet:
    async def test_get_found(self, session, test_product):
        result = await product_repo.get(session, id=test_product.id)
        assert result is not None
        assert result.id == test_product.id

    async def test_get_not_found(self, session):
        result = await product_repo.get(session, id=NONEXISTENT_ID)
        assert result is None


@pytest.mark.asyncio
class TestProductRepositoryCreate:
    async def test_create_product(self, session):
        unique_id = uuid.uuid4().hex[:8]
        product_in = ProductCreate(
            name=f"Repo Product {unique_id}",
            sku=f"REPO-{unique_id}",
            price=Decimal("49.99"),
            category="repo_test",
        )
        product = await product_repo.create(session, product_in)
        assert product.id is not None
        assert product.sku == f"REPO-{unique_id}"
        assert product.price == Decimal("49.99")


@pytest.mark.asyncio
class TestProductRepositoryMulti:
    async def test_get_multi(self, session, multiple_products):
        products = await product_repo.get_multi(session, skip=0, limit=10)
        assert len(products) >= 5

    async def test_count(self, session, multiple_products):
        count = await product_repo.count(session)
        assert count >= 5
