from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.orders import service as order_service
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderItemCreate, OrderUpdate


@pytest.mark.asyncio
class TestOrderServiceCreate:
    async def test_create_order_success(self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch):
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
        assert len(result.scalar_one().items) == 2

    async def test_create_order_single_item(
        self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch
    ):
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("99.99"))],
        )
        order = await order_service.create_order(session, order_in)
        assert order.total_amount == Decimal("99.99")
        result = await session.execute(select(Order).options(selectinload(Order.items)).where(Order.id == order.id))
        assert len(result.scalar_one().items) == 1

    async def test_create_order_total_calculation(
        self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch
    ):
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(product_id=test_product_for_order.id, quantity=3, unit_price=Decimal("10.00")),
                OrderItemCreate(product_id=test_product_for_order.id, quantity=2, unit_price=Decimal("5.50")),
            ],
        )
        order = await order_service.create_order(session, order_in)
        assert order.total_amount == Decimal("41.00")

    async def test_create_order_dispatches_timeout_task(self, session: AsyncSession, test_user, test_product_for_order):
        from unittest.mock import patch

        with patch("app.modules.orders.service.dispatch") as mock_dispatch:
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("99.99"))],
            )
            order = await order_service.create_order(session, order_in)
            mock_dispatch.assert_called_once()
            assert mock_dispatch.call_args[0][1] == order.id
            assert "countdown" in mock_dispatch.call_args.kwargs


@pytest.mark.asyncio
class TestOrderServiceGet:
    async def test_get_order_by_id_found(self, session: AsyncSession, test_order):
        order = await order_service.get_order_by_id(session, test_order.id)
        assert order is not None
        assert order.id == test_order.id
        assert order.user_id == test_order.user_id

    async def test_get_order_by_id_not_found(self, session: AsyncSession):
        assert await order_service.get_order_by_id(session, 99999) is None

    async def test_get_order_with_items_found(self, session: AsyncSession, test_order):
        order = await order_service.get_order_with_items(session, test_order.id)
        assert order is not None
        assert len(order.items) > 0

    async def test_get_order_with_items_not_found(self, session: AsyncSession):
        assert await order_service.get_order_with_items(session, 99999) is None


@pytest.mark.asyncio
class TestOrderServiceList:
    async def test_get_orders_pagination(
        self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch
    ):
        for _ in range(5):
            await order_service.create_order(
                session,
                OrderCreate(
                    user_id=test_user.id,
                    items=[
                        OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))
                    ],
                ),
            )
        assert len(await order_service.get_orders(session, skip=0, limit=3)) == 3
        assert len(await order_service.get_orders(session, skip=3, limit=3)) >= 2

    async def test_get_orders_by_user(self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch):
        await order_service.create_order(
            session,
            OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            ),
        )
        orders = await order_service.get_orders_by_user(session, test_user.id)
        assert len(orders) >= 1
        assert all(o.user_id == test_user.id for o in orders)

    async def test_get_orders_by_status(self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch):
        await order_service.create_order(
            session,
            OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            ),
        )
        orders = await order_service.get_orders_by_status(session, OrderStatus.PENDING)
        assert len(orders) >= 1
        assert all(o.status == OrderStatus.PENDING.value for o in orders)

    async def test_get_orders_count(self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch):
        initial = await order_service.get_orders_count(session)
        await order_service.create_order(
            session,
            OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            ),
        )
        assert await order_service.get_orders_count(session) == initial + 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "before,after",
    [
        (OrderStatus.PENDING, OrderStatus.CONFIRMED),
        (OrderStatus.PENDING, OrderStatus.CANCELLED),
        (OrderStatus.CONFIRMED, OrderStatus.SHIPPED),
        (OrderStatus.CONFIRMED, OrderStatus.CANCELLED),
        (OrderStatus.SHIPPED, OrderStatus.COMPLETED),
    ],
)
class TestOrderServiceValidTransitions:
    async def test_valid_transition(self, session: AsyncSession, fresh_order, before, after):
        if fresh_order.status != before.value:
            fresh_order.status = before.value
            await session.commit()
        updated = await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=after))
        assert updated.status == after.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "before,invalid",
    [
        (OrderStatus.COMPLETED, OrderStatus.CANCELLED),
        (OrderStatus.COMPLETED, OrderStatus.PENDING),
        (OrderStatus.CANCELLED, OrderStatus.CONFIRMED),
        (OrderStatus.PENDING, OrderStatus.SHIPPED),
    ],
)
class TestOrderServiceInvalidTransitions:
    async def test_invalid_transition(self, session: AsyncSession, fresh_order, before, invalid):
        if fresh_order.status != before.value:
            fresh_order.status = before.value
            await session.commit()
        with pytest.raises(ValidationException):
            await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=invalid))


@pytest.mark.asyncio
class TestOrderServiceUpdateNotFound:
    async def test_update_order_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundException):
            await order_service.update_order_status(session, 99999, OrderUpdate(status=OrderStatus.CONFIRMED))


@pytest.mark.asyncio
class TestOrderServiceDelete:
    async def test_delete_order_found(self, session: AsyncSession, fresh_order):
        deleted = await order_service.delete_order(session, fresh_order.id)
        assert deleted.id == fresh_order.id
        assert await order_service.get_order_by_id(session, fresh_order.id) is None

    async def test_delete_order_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundException):
            await order_service.delete_order(session, 99999)
