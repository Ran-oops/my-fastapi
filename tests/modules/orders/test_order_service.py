import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.orders import service as order_service
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderItemCreate, OrderUpdate
from app.modules.products.schemas import ProductCreate
from app.modules.products import service as product_service


@pytest.mark.asyncio
class TestOrderServiceCreate:
    """Tests for order creation."""

    async def test_create_order_success(self, session, test_user, test_product_for_order):
        """Test successful order creation with multiple items."""
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[
                    OrderItemCreate(product_id=test_product_for_order.id, quantity=2, unit_price=Decimal("99.99")),
                    OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("50.00")),
                ],
            )
            order = await order_service.create_order(session, order_in)

            assert order.id is not None
            assert order.user_id == test_user.id
            assert order.status == OrderStatus.PENDING.value
            assert order.total_amount == Decimal("249.98")
            result = await session.execute(select(Order).options(selectinload(Order.items)).where(Order.id == order.id))
            order_with_items = result.scalar_one()
            assert len(order_with_items.items) == 2

    async def test_create_order_single_item(self, session, test_user, test_product_for_order):
        """Test order creation with single item."""
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("99.99"))],
            )
            order = await order_service.create_order(session, order_in)

            assert order.id is not None
            result = await session.execute(select(Order).options(selectinload(Order.items)).where(Order.id == order.id))
            order_with_items = result.scalar_one()
            assert len(order_with_items.items) == 1
            assert order.total_amount == Decimal("99.99")

    async def test_create_order_total_calculation(self, session, test_user, test_product_for_order):
        """Test total amount is calculated correctly."""
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[
                    OrderItemCreate(product_id=test_product_for_order.id, quantity=3, unit_price=Decimal("10.00")),
                    OrderItemCreate(product_id=test_product_for_order.id, quantity=2, unit_price=Decimal("5.50")),
                ],
            )
            order = await order_service.create_order(session, order_in)

            assert order.total_amount == Decimal("41.00")

    async def test_create_order_dispatches_timeout_task(self, session, test_user, test_product_for_order):
        """Test that timeout cancellation task is dispatched."""
        with patch("app.modules.orders.service.dispatch") as mock_dispatch:
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("99.99"))],
            )
            order = await order_service.create_order(session, order_in)

            mock_dispatch.assert_called_once()
            call_args = mock_dispatch.call_args
            assert call_args[0][0].__name__ == "cancel_timeout"
            assert call_args[0][1] == order.id
            assert "countdown" in call_args.kwargs
