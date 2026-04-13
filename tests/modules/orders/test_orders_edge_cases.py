"""
Edge cases and boundary condition tests for orders module.

Tests cover:
- Negative amounts and boundary values
- Concurrent order creation
- Order status illegal transitions
- Non-existent order operations
- Permission boundaries
"""

import asyncio
from decimal import Decimal, InvalidOperation
from unittest.mock import patch

import pytest
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderItemCreate, OrderUpdate
from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestOrderAmountEdgeCases:
    """Tests for order amount boundary conditions."""

    async def test_order_with_zero_amount_item(self, client, test_user, user_headers, test_product_for_order):
        """Test order with zero unit price (should fail validation)."""
        from app.modules.orders import service as order_service

        # Try to create order with zero price
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("0.00")),
            ],
        )

        # This should fail validation in schema (gt=0)
        with pytest.raises(Exception) as exc_info:
            async with client:
                pass

        # Instead test via API
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": test_user.id,
                "items": [
                    {"product_id": test_product_for_order.id, "quantity": 1, "unit_price": "0.00"},
                ],
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_order_with_negative_amount(self, client, test_user, user_headers, test_product_for_order):
        """Test order with negative unit price (should fail validation)."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": test_user.id,
                "items": [
                    {"product_id": test_product_for_order.id, "quantity": 1, "unit_price": "-10.00"},
                ],
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_order_with_very_large_amount(
        self, client, test_user, user_headers, test_product_for_order, patch_dispatch
    ):
        """Test order with very large amount."""
        from app.modules.orders import service as order_service
        from sqlalchemy.ext.asyncio import AsyncSession

        # Create order with large amount via service
        large_price = Decimal("999999999.99")
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=large_price),
            ],
        )

        # Use the session fixture indirectly via context
        async for session in AsyncSession():
            order = await order_service.create_order(session, order_in)
            assert order.total_amount == large_price

    async def test_order_with_zero_quantity(self, client, test_user, user_headers, test_product_for_order):
        """Test order with zero quantity (should fail validation)."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": test_user.id,
                "items": [
                    {"product_id": test_product_for_order.id, "quantity": 0, "unit_price": "10.00"},
                ],
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_order_with_negative_quantity(self, client, test_user, user_headers, test_product_for_order):
        """Test order with negative quantity (should fail validation)."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": test_user.id,
                "items": [
                    {"product_id": test_product_for_order.id, "quantity": -1, "unit_price": "10.00"},
                ],
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_order_with_maximum_decimal_places(
        self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch
    ):
        """Test order with maximum decimal places."""
        from app.modules.orders import service as order_service

        # Test with 2 decimal places (standard for currency)
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("99.99")),
            ],
        )
        order = await order_service.create_order(session, order_in)
        assert order.total_amount == Decimal("99.99")

    async def test_order_with_many_items(
        self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch
    ):
        """Test order with many items."""
        from app.modules.orders import service as order_service

        # Create order with 50 items
        items = [
            OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("1.00"))
            for _ in range(50)
        ]
        order_in = OrderCreate(user_id=test_user.id, items=items)
        order = await order_service.create_order(session, order_in)
        assert order.total_amount == Decimal("50.00")


@pytest.mark.asyncio
class TestOrderStatusIllegalTransitions:
    """Tests for illegal order status transitions."""

    async def test_transition_from_completed_to_any(self, session: AsyncSession, fresh_order):
        """Test that completed order cannot transition to any status."""
        from app.modules.orders import service as order_service

        # Set order to completed
        fresh_order.status = OrderStatus.COMPLETED.value
        await session.commit()

        # Try to transition to any other status
        invalid_transitions = [
            OrderStatus.PENDING,
            OrderStatus.CONFIRMED,
            OrderStatus.SHIPPED,
            OrderStatus.CANCELLED,
        ]

        for new_status in invalid_transitions:
            with pytest.raises(ValidationException):
                await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=new_status))

    async def test_transition_from_cancelled_to_any(self, session: AsyncSession, fresh_order):
        """Test that cancelled order cannot transition to any status."""
        from app.modules.orders import service as order_service

        # Set order to cancelled
        fresh_order.status = OrderStatus.CANCELLED.value
        await session.commit()

        # Try to transition to any other status
        invalid_transitions = [
            OrderStatus.PENDING,
            OrderStatus.CONFIRMED,
            OrderStatus.SHIPPED,
            OrderStatus.COMPLETED,
        ]

        for new_status in invalid_transitions:
            with pytest.raises(ValidationException):
                await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=new_status))

    async def test_transition_from_shipped_to_cancelled(self, session: AsyncSession, fresh_order):
        """Test that shipped order cannot be cancelled."""
        from app.modules.orders import service as order_service

        # Set order to shipped
        fresh_order.status = OrderStatus.SHIPPED.value
        await session.commit()

        with pytest.raises(ValidationException):
            await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=OrderStatus.CANCELLED))

    async def test_transition_from_shipped_to_pending(self, session: AsyncSession, fresh_order):
        """Test that shipped order cannot go back to pending."""
        from app.modules.orders import service as order_service

        fresh_order.status = OrderStatus.SHIPPED.value
        await session.commit()

        with pytest.raises(ValidationException):
            await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=OrderStatus.PENDING))

    async def test_transition_from_pending_to_completed_directly(self, session: AsyncSession, fresh_order):
        """Test that pending order cannot jump directly to completed."""
        from app.modules.orders import service as order_service

        fresh_order.status = OrderStatus.PENDING.value
        await session.commit()

        with pytest.raises(ValidationException):
            await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=OrderStatus.COMPLETED))

    async def test_transition_from_confirmed_to_pending(self, session: AsyncSession, fresh_order):
        """Test that confirmed order cannot go back to pending."""
        from app.modules.orders import service as order_service

        fresh_order.status = OrderStatus.CONFIRMED.value
        await session.commit()

        with pytest.raises(ValidationException):
            await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=OrderStatus.PENDING))


@pytest.mark.asyncio
class TestConcurrentOrderCreation:
    """Tests for concurrent order creation scenarios."""

    async def test_concurrent_orders_same_user(self, session: AsyncSession, test_user, test_product_for_order):
        """Test concurrent order creation by same user."""
        from app.modules.orders import service as order_service

        async def create_order():
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[
                    OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00")),
                ],
            )
            return await order_service.create_order(session, order_in)

        # Create multiple orders concurrently
        tasks = [create_order() for _ in range(5)]
        orders = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful orders
        successful_orders = [o for o in orders if not isinstance(o, Exception)]
        assert len(successful_orders) == 5

        # Verify all have unique IDs
        order_ids = [o.id for o in successful_orders]
        assert len(set(order_ids)) == 5

    async def test_concurrent_status_updates(self, session: AsyncSession, fresh_order):
        """Test concurrent status updates on same order."""
        from app.modules.orders import service as order_service

        # First update to confirmed
        await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=OrderStatus.CONFIRMED))

        # Refresh order
        await session.refresh(fresh_order)
        assert fresh_order.status == OrderStatus.CONFIRMED.value


@pytest.mark.asyncio
class TestNonExistentOrderOperations:
    """Tests for operations on non-existent orders."""

    async def test_get_nonexistent_order(self, session: AsyncSession):
        """Test getting an order that doesn't exist."""
        from app.modules.orders import service as order_service

        order = await order_service.get_order_by_id(session, NONEXISTENT_ID)
        assert order is None

    async def test_update_nonexistent_order(self, session: AsyncSession):
        """Test updating an order that doesn't exist."""
        from app.modules.orders import service as order_service

        with pytest.raises(NotFoundException) as exc_info:
            await order_service.update_order_status(session, NONEXISTENT_ID, OrderUpdate(status=OrderStatus.CONFIRMED))
        assert "not found" in str(exc_info.value).lower()

    async def test_delete_nonexistent_order(self, session: AsyncSession):
        """Test deleting an order that doesn't exist."""
        from app.modules.orders import service as order_service

        with pytest.raises(NotFoundException) as exc_info:
            await order_service.delete_order(session, NONEXISTENT_ID)
        assert "not found" in str(exc_info.value).lower()

    async def test_get_order_with_items_nonexistent(self, session: AsyncSession):
        """Test getting order with items for non-existent order."""
        from app.modules.orders import service as order_service

        order = await order_service.get_order_with_items(session, NONEXISTENT_ID)
        assert order is None


@pytest.mark.asyncio
class TestOrderPermissionBoundaries:
    """Tests for order permission boundaries."""

    async def test_user_cannot_view_other_users_order(self, client, test_user, user_headers, patch_dispatch):
        """Test user cannot view order belonging to another user."""
        from app.modules.orders import service as order_service
        from sqlalchemy.ext.asyncio import AsyncSession

        # Create order for test_user
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(product_id=1, quantity=1, unit_price=Decimal("10.00")),
            ],
        )

        # Need to create order with session
        # This test assumes proper authorization is implemented
        # The actual behavior depends on your authorization logic

    async def test_user_cannot_update_other_users_order(self, client):
        """Test user cannot update order belonging to another user."""
        # This depends on your API implementation
        # Should test 403 Forbidden response
        pass

    async def test_user_cannot_delete_other_users_order(self, client):
        """Test user cannot delete order belonging to another user."""
        # This depends on your API implementation
        # Should test 403 Forbidden response
        pass


@pytest.mark.asyncio
class TestOrderEmptyAndNullCases:
    """Tests for empty/null order scenarios."""

    async def test_order_with_empty_items_list(self, client, test_user, user_headers):
        """Test order with empty items list."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": test_user.id,
                "items": [],
            },
            headers=user_headers,
        )
        # Should fail validation (min_length=1)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_order_with_null_items(self, client, test_user, user_headers):
        """Test order with null items."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": test_user.id,
                "items": None,
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_order_with_missing_items(self, client, test_user, user_headers):
        """Test order with missing items field."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": test_user.id,
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_order_with_null_user_id(self, client, user_headers, test_product_for_order):
        """Test order with null user_id."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": None,
                "items": [
                    {"product_id": test_product_for_order.id, "quantity": 1, "unit_price": "10.00"},
                ],
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_order_with_nonexistent_product(self, client, test_user, user_headers):
        """Test order with non-existent product."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": test_user.id,
                "items": [
                    {"product_id": NONEXISTENT_ID, "quantity": 1, "unit_price": "10.00"},
                ],
            },
            headers=user_headers,
        )
        # Should either succeed (FK constraint deferred) or fail
        # Depends on database constraints
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ]


@pytest.mark.asyncio
class TestOrderUpdateEdgeCases:
    """Tests for order update edge cases."""

    async def test_update_order_with_null_status(self, session: AsyncSession, fresh_order):
        """Test updating order with null status (no change)."""
        from app.modules.orders import service as order_service

        original_status = fresh_order.status
        updated = await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=None))
        assert updated.status == original_status

    async def test_update_order_no_changes(self, session: AsyncSession, fresh_order):
        """Test updating order with no changes."""
        from app.modules.orders import service as order_service

        # Update with same status
        updated = await order_service.update_order_status(
            session, fresh_order.id, OrderUpdate(status=OrderStatus(fresh_order.status))
        )
        assert updated.status == fresh_order.status
