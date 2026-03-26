import uuid
from decimal import Decimal

import pytest_asyncio

from app.modules.products import service as product_service
from app.modules.products.schemas import ProductCreate


@pytest_asyncio.fixture
async def test_product(session):
    product_in = ProductCreate(
        name="Test Product",
        sku=f"TEST-{uuid.uuid4().hex[:8]}",
        description="A test product",
        price=Decimal("99.99"),
        category="test",
    )
    return await product_service.create_product(session, product_in)


@pytest_asyncio.fixture
async def multiple_products(session):
    products = []
    categories = ["electronics", "clothing", "electronics", "books", "food"]
    for i in range(5):
        product_in = ProductCreate(
            name=f"Product {i + 1}",
            sku=f"MULTI-{uuid.uuid4().hex[:8]}-{i}",
            description=f"Test product {i + 1}",
            price=Decimal(f"{(i + 1) * 10}.00"),
            category=categories[i],
        )
        products.append(await product_service.create_product(session, product_in))
    return products
