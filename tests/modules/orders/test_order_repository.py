from decimal import Decimal

import pytest

from app.modules.orders.models import OrderStatus
from app.modules.orders.repository import order_repo
from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestOrderRepositoryGetByUser:
    async def test_get_by_user_returns_user_orders(self, session, test_user, test_product_for_order):
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("50.00"))],
        )
        from unittest.mock import patch

        with patch("app.modules.orders.service.dispatch"):
            from app.modules.orders import service as order_service

            await order_service.create_order(session, order_in)

        orders = await order_repo.get_by_user(session, user_id=test_user.id)
        assert len(orders) >= 1
        assert all(o.user_id == test_user.id for o in orders)

    async def test_get_by_user_empty_for_other_user(self, session):
        orders = await order_repo.get_by_user(session, user_id=NONEXISTENT_ID)
        assert len(orders) == 0


@pytest.mark.asyncio
class TestOrderRepositoryGetByStatus:
    async def test_get_by_status_returns_matching_orders(self, session, test_user, test_product_for_order):
        from unittest.mock import patch

        from app.modules.orders import service as order_service

        order_in = OrderCreate(
            user_id=test_user.id,
            items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("25.00"))],
        )
        with patch("app.modules.orders.service.dispatch"):
            await order_service.create_order(session, order_in)

        orders = await order_repo.get_by_status(session, status=OrderStatus.PENDING)
        assert len(orders) >= 1
        assert all(o.status == OrderStatus.PENDING.value for o in orders)

    async def test_get_by_status_empty(self, session):
        orders = await order_repo.get_by_status(session, status=OrderStatus.COMPLETED)
        assert isinstance(orders, list)


@pytest.mark.asyncio
class TestOrderRepositoryGetWithItems:
    async def test_get_with_items_loads_items(self, session, fresh_order):
        order = await order_repo.get_with_items(session, fresh_order.id)
        assert order is not None
        assert len(order.items) >= 1


@pytest.mark.asyncio
class TestOrderRepositoryGet:
    async def test_get_found(self, session, fresh_order):
        order = await order_repo.get(session, id=fresh_order.id)
        assert order is not None
        assert order.id == fresh_order.id

    async def test_get_not_found(self, session):
        order = await order_repo.get(session, id=NONEXISTENT_ID)
        assert order is None


@pytest.mark.asyncio
class TestOrderRepositoryMulti:
    async def test_get_multi(self, session, fresh_order):
        orders = await order_repo.get_multi(session, skip=0, limit=10)
        assert len(orders) >= 1

    async def test_count(self, session, fresh_order):
        count = await order_repo.count(session)
        assert count >= 1
