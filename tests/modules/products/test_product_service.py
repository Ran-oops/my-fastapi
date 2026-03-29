import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.products import service as product_service
from app.modules.products.schemas import ProductCreate, ProductUpdate
from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestProductServiceCreate:
    async def test_create_product_success(self, session: AsyncSession):
        product_in = ProductCreate(
            name="New Product",
            sku=f"NEW-{uuid.uuid4().hex[:8]}",
            description="A new product",
            price=Decimal("49.99"),
            category="new",
        )
        product = await product_service.create_product(session, product_in)
        assert product.id is not None
        assert product.name == product_in.name
        assert product.sku == product_in.sku
        assert product.price == product_in.price
        assert product.category == product_in.category
        assert product.is_active is True

    async def test_create_product_duplicate_sku(self, session: AsyncSession, test_product):
        with pytest.raises(ConflictException):
            await product_service.create_product(
                session,
                ProductCreate(
                    name="Duplicate",
                    sku=test_product.sku,
                    price=Decimal("19.99"),
                ),
            )

    async def test_create_product_negative_price(self, session: AsyncSession):
        with pytest.raises(ValidationError):
            ProductCreate(
                name="Negative",
                sku=f"NEG-{uuid.uuid4().hex[:8]}",
                price=Decimal("-10.00"),
            )


@pytest.mark.asyncio
class TestProductServiceGet:
    async def test_get_product_by_id_found(self, session: AsyncSession, test_product):
        product = await product_service.get_product_by_id(session, test_product.id)
        assert product is not None
        assert product.id == test_product.id
        assert product.sku == test_product.sku

    async def test_get_product_by_id_not_found(self, session: AsyncSession):
        assert await product_service.get_product_by_id(session, NONEXISTENT_ID) is None

    async def test_get_product_by_sku_found(self, session: AsyncSession, test_product):
        product = await product_service.get_product_by_sku(session, test_product.sku)
        assert product is not None
        assert product.id == test_product.id

    async def test_get_product_by_sku_not_found(self, session: AsyncSession):
        assert await product_service.get_product_by_sku(session, "NONEXISTENT-SKU") is None


@pytest.mark.asyncio
class TestProductServiceList:
    async def test_get_products_pagination(self, session: AsyncSession, multiple_products):
        assert len(await product_service.get_products(session, skip=0, limit=3)) == 3
        assert len(await product_service.get_products(session, skip=3, limit=3)) >= 2

    async def test_get_products_by_category(self, session: AsyncSession, multiple_products):
        products = await product_service.get_products_by_category(session, "electronics", skip=0, limit=100)
        assert len(products) >= 2
        assert all(p.category == "electronics" for p in products)

    async def test_get_products_count(self, session: AsyncSession, multiple_products):
        assert await product_service.get_products_count(session) >= 5


@pytest.mark.asyncio
class TestProductServiceUpdate:
    async def test_update_product_success(self, session: AsyncSession, test_product):
        product = await product_service.update_product(
            session, test_product.id, ProductUpdate(name="Updated", price=Decimal("149.99"))
        )
        assert product.name == "Updated"
        assert product.price == Decimal("149.99")
        assert product.sku == test_product.sku

    async def test_update_product_partial(self, session: AsyncSession, test_product):
        product = await product_service.update_product(
            session, test_product.id, ProductUpdate(description="Updated description only")
        )
        assert product.description == "Updated description only"
        assert product.name == test_product.name

    async def test_update_product_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundException):
            await product_service.update_product(session, NONEXISTENT_ID, ProductUpdate(name="X"))


@pytest.mark.asyncio
class TestProductServiceDelete:
    async def test_delete_product_found(self, session: AsyncSession):
        product_in = ProductCreate(
            name="To Delete",
            sku=f"DEL-{uuid.uuid4().hex[:8]}",
            price=Decimal("19.99"),
        )
        product = await product_service.create_product(session, product_in)
        deleted = await product_service.delete_product(session, product.id)
        assert deleted.id == product.id
        assert await product_service.get_product_by_id(session, product.id) is None

    async def test_delete_product_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundException):
            await product_service.delete_product(session, NONEXISTENT_ID)
