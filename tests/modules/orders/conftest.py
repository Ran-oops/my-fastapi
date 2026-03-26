import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest_asyncio

from app.modules.orders import service as order_service
from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from app.modules.products import service as product_service
from app.modules.products.schemas import ProductCreate


@pytest_asyncio.fixture
async def test_product_for_order(session):
    """Create a product for order tests."""
    product_in = ProductCreate(
        name="Test Product for Order",
        sku=f"TEST-ORDER-{uuid.uuid4().hex[:8]}",
        price=Decimal("99.99"),
        category="test",
    )
    return await product_service.create_product(session, product_in)


@pytest_asyncio.fixture
async def test_order(session, test_user, test_product_for_order):
    """Create a test order with items."""
    with patch("app.modules.orders.service.dispatch"):
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(
                    product_id=test_product_for_order.id,
                    quantity=2,
                    unit_price=test_product_for_order.price,
                )
            ],
        )
        return await order_service.create_order(session, order_in)


@pytest_asyncio.fixture
def patch_dispatch():
    """Mock the Celery dispatch to avoid real task execution."""
    with patch("app.modules.orders.service.dispatch"):
        yield


@pytest_asyncio.fixture
async def fresh_order(session, test_user, test_product_for_order, patch_dispatch):
    """Create a fresh PENDING order for each test that needs one."""
    order_in = OrderCreate(
        user_id=test_user.id,
        items=[
            OrderItemCreate(
                product_id=test_product_for_order.id,
                quantity=1,
                unit_price=Decimal("10.00"),
            )
        ],
    )
    return await order_service.create_order(session, order_in)
