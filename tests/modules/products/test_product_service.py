import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.products import service as product_service
from app.modules.products.schemas import ProductCreate, ProductUpdate


@pytest.mark.asyncio
class TestProductServiceCreate:
    async def test_create_product_success(self, session):
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

    async def test_create_product_duplicate_sku(self, session, test_product):
        product_in = ProductCreate(
            name="Duplicate SKU Product",
            sku=test_product.sku,
            price=Decimal("19.99"),
            category="test",
        )

        with pytest.raises(ConflictException):
            await product_service.create_product(session, product_in)

    async def test_create_product_negative_price(self, session):
        with pytest.raises(ValidationError):
            ProductCreate(
                name="Negative Price Product",
                sku=f"NEG-{uuid.uuid4().hex[:8]}",
                price=Decimal("-10.00"),
                category="test",
            )


@pytest.mark.asyncio
class TestProductServiceGet:
    async def test_get_product_by_id_found(self, session, test_product):
        product = await product_service.get_product_by_id(session, test_product.id)

        assert product is not None
        assert product.id == test_product.id
        assert product.name == test_product.name
        assert product.sku == test_product.sku

    async def test_get_product_by_id_not_found(self, session):
        product = await product_service.get_product_by_id(session, 99999)

        assert product is None

    async def test_get_product_by_sku_found(self, session, test_product):
        product = await product_service.get_product_by_sku(session, test_product.sku)

        assert product is not None
        assert product.sku == test_product.sku
        assert product.id == test_product.id

    async def test_get_product_by_sku_not_found(self, session):
        product = await product_service.get_product_by_sku(session, "NONEXISTENT-SKU")

        assert product is None


@pytest.mark.asyncio
class TestProductServiceList:
    async def test_get_products_pagination(self, session, multiple_products):
        products = await product_service.get_products(session, skip=0, limit=3)
        assert len(products) == 3

        products2 = await product_service.get_products(session, skip=3, limit=3)
        assert len(products2) >= 2

    async def test_get_products_by_category(self, session, multiple_products):
        products = await product_service.get_products_by_category(session, "electronics", skip=0, limit=100)

        electronics_count = sum(1 for p in multiple_products if p.category == "electronics")
        assert len(products) >= electronics_count
        for product in products:
            assert product.category == "electronics"

    async def test_get_products_count(self, session, multiple_products):
        count = await product_service.get_products_count(session)

        assert count >= 5


@pytest.mark.asyncio
class TestProductServiceUpdate:
    async def test_update_product_success(self, session, test_product):
        update_data = ProductUpdate(
            name="Updated Product Name",
            price=Decimal("149.99"),
        )
        product = await product_service.update_product(session, test_product.id, update_data)

        assert product.name == "Updated Product Name"
        assert product.price == Decimal("149.99")
        assert product.sku == test_product.sku

    async def test_update_product_partial(self, session, test_product):
        update_data = ProductUpdate(description="Updated description only")
        product = await product_service.update_product(session, test_product.id, update_data)

        assert product.description == "Updated description only"
        assert product.name == test_product.name
        assert product.price == test_product.price

    async def test_update_product_not_found(self, session):
        update_data = ProductUpdate(name="Non-existent")
        with pytest.raises(NotFoundException):
            await product_service.update_product(session, 99999, update_data)


@pytest.mark.asyncio
class TestProductServiceDelete:
    async def test_delete_product_found(self, session):
        product_in = ProductCreate(
            name="Product to Delete",
            sku=f"DEL-{uuid.uuid4().hex[:8]}",
            price=Decimal("19.99"),
            category="test",
        )
        product = await product_service.create_product(session, product_in)

        deleted = await product_service.delete_product(session, product.id)
        assert deleted.id == product.id

        result = await product_service.get_product_by_id(session, product.id)
        assert result is None

    async def test_delete_product_not_found(self, session):
        with pytest.raises(NotFoundException):
            await product_service.delete_product(session, 99999)
