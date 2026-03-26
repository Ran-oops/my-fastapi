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


@pytest.mark.asyncio
class TestOrderServiceGet:
    async def test_get_order_by_id_found(self, session, test_order):
        order = await order_service.get_order_by_id(session, test_order.id)
        assert order is not None
        assert order.id == test_order.id
        assert order.user_id == test_order.user_id

    async def test_get_order_by_id_not_found(self, session):
        order = await order_service.get_order_by_id(session, 99999)
        assert order is None

    async def test_get_order_with_items_found(self, session, test_order):
        order = await order_service.get_order_with_items(session, test_order.id)
        assert order is not None
        assert order.id == test_order.id
        assert len(order.items) > 0

    async def test_get_order_with_items_not_found(self, session):
        order = await order_service.get_order_with_items(session, 99999)
        assert order is None


@pytest.mark.asyncio
class TestOrderServiceList:
    async def test_get_orders_pagination(self, session, test_user, test_product_for_order):
        with patch("app.modules.orders.service.dispatch"):
            for _ in range(5):
                order_in = OrderCreate(
                    user_id=test_user.id,
                    items=[
                        OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))
                    ],
                )
                await order_service.create_order(session, order_in)

        orders = await order_service.get_orders(session, skip=0, limit=3)
        assert len(orders) == 3
        orders2 = await order_service.get_orders(session, skip=3, limit=3)
        assert len(orders2) >= 2

    async def test_get_orders_by_user(self, session, test_user, test_product_for_order):
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            )
            await order_service.create_order(session, order_in)

        orders = await order_service.get_orders_by_user(session, test_user.id)
        assert len(orders) >= 1
        for order in orders:
            assert order.user_id == test_user.id

    async def test_get_orders_by_status(self, session, test_user, test_product_for_order):
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            )
            await order_service.create_order(session, order_in)

        orders = await order_service.get_orders_by_status(session, OrderStatus.PENDING)
        assert len(orders) >= 1
        for order in orders:
            assert order.status == OrderStatus.PENDING.value

    async def test_get_orders_count(self, session, test_user, test_product_for_order):
        initial_count = await order_service.get_orders_count(session)
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            )
            await order_service.create_order(session, order_in)
        new_count = await order_service.get_orders_count(session)
        assert new_count == initial_count + 1


@pytest.mark.asyncio
class TestOrderServiceStatusTransitions:
    async def test_update_status_pending_to_confirmed(self, session, test_order):
        assert test_order.status == OrderStatus.PENDING.value
        update = OrderUpdate(status=OrderStatus.CONFIRMED)
        order = await order_service.update_order_status(session, test_order.id, update)
        assert order.status == OrderStatus.CONFIRMED.value

    async def test_update_status_pending_to_cancelled(self, session, test_user, test_product_for_order):
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            )
            order = await order_service.create_order(session, order_in)

        update = OrderUpdate(status=OrderStatus.CANCELLED)
        updated = await order_service.update_order_status(session, order.id, update)
        assert updated.status == OrderStatus.CANCELLED.value

    async def test_update_status_confirmed_to_shipped(self, session, test_user, test_product_for_order):
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            )
            order = await order_service.create_order(session, order_in)

        await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.CONFIRMED))
        updated = await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.SHIPPED))
        assert updated.status == OrderStatus.SHIPPED.value

    async def test_update_status_confirmed_to_cancelled(self, session, test_user, test_product_for_order):
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            )
            order = await order_service.create_order(session, order_in)

        await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.CONFIRMED))
        updated = await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.CANCELLED))
        assert updated.status == OrderStatus.CANCELLED.value

    async def test_update_status_shipped_to_completed(self, session, test_user, test_product_for_order):
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            )
            order = await order_service.create_order(session, order_in)

        await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.CONFIRMED))
        await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.SHIPPED))
        updated = await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.COMPLETED))
        assert updated.status == OrderStatus.COMPLETED.value

    async def test_update_status_completed_to_any_fails(self, session, test_user, test_product_for_order):
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            )
            order = await order_service.create_order(session, order_in)

        await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.CONFIRMED))
        await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.SHIPPED))
        await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.COMPLETED))

        with pytest.raises(ValidationException):
            await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.CANCELLED))

    async def test_update_status_cancelled_to_any_fails(self, session, test_user, test_product_for_order):
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            )
            order = await order_service.create_order(session, order_in)

        await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.CANCELLED))

        with pytest.raises(ValidationException):
            await order_service.update_order_status(session, order.id, OrderUpdate(status=OrderStatus.CONFIRMED))

    async def test_update_status_pending_to_shipped_fails(self, session, test_order):
        with pytest.raises(ValidationException):
            await order_service.update_order_status(session, test_order.id, OrderUpdate(status=OrderStatus.SHIPPED))

    async def test_update_status_order_not_found(self, session):
        with pytest.raises(NotFoundException):
            await order_service.update_order_status(session, 99999, OrderUpdate(status=OrderStatus.CONFIRMED))


@pytest.mark.asyncio
class TestOrderServiceDelete:
    async def test_delete_order_found(self, session, test_user, test_product_for_order):
        with patch("app.modules.orders.service.dispatch"):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            )
            order = await order_service.create_order(session, order_in)

        deleted = await order_service.delete_order(session, order.id)
        assert deleted.id == order.id

        result = await order_service.get_order_by_id(session, order.id)
        assert result is None

    async def test_delete_order_not_found(self, session):
        with pytest.raises(NotFoundException):
            await order_service.delete_order(session, 99999)
