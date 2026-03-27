from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.eventbus import Event, eventbus
from app.core.events import ORDER_CANCELLED, ORDER_CONFIRMED, ORDER_SHIPPED
from app.core.exceptions import NotFoundException, ValidationException
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.orders.repository import order_repo
from app.modules.orders.schemas import OrderCreate, OrderUpdate
from app.modules.orders.tasks import cancel_timeout
from app.tasks.dispatcher import dispatch


async def get_order_by_id(session: AsyncSession, order_id: int) -> Order | None:
    return await order_repo.get(session, id=order_id)


async def get_order_with_items(session: AsyncSession, order_id: int) -> Order | None:
    return await order_repo.get_with_items(session, order_id)


async def get_orders(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[Order]:
    return await order_repo.get_multi(session, skip=skip, limit=limit)


async def get_orders_by_user(session: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> list[Order]:
    return await order_repo.get_by_user(session, user_id, skip=skip, limit=limit)


async def get_orders_by_status(
    session: AsyncSession, status: OrderStatus, skip: int = 0, limit: int = 100
) -> list[Order]:
    return await order_repo.get_by_status(session, status, skip=skip, limit=limit)


async def get_orders_count(session: AsyncSession) -> int:
    return await order_repo.count(session)


async def create_order(session: AsyncSession, data: OrderCreate) -> Order:
    total_amount = Decimal("0.00")
    order = Order(user_id=data.user_id, total_amount=total_amount)
    session.add(order)
    await session.flush()

    for item_data in data.items:
        item_total = Decimal(str(item_data.quantity)) * item_data.unit_price
        total_amount += item_total
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
        )
        session.add(order_item)

    order.total_amount = total_amount
    await session.commit()
    await session.refresh(order)
    dispatch(cancel_timeout, order.id, countdown=settings.ORDER_CANCEL_TIMEOUT)
    return order


def _validate_status_transition(current_status: str, new_status: OrderStatus) -> None:
    current = OrderStatus(current_status)
    valid_transitions = {
        OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
        OrderStatus.CONFIRMED: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
        OrderStatus.SHIPPED: [OrderStatus.COMPLETED],
        OrderStatus.COMPLETED: [],
        OrderStatus.CANCELLED: [],
    }

    if new_status not in valid_transitions.get(current, []):
        raise ValidationException(f"Cannot transition from {current.value} to {new_status.value}")


async def update_order_status(session: AsyncSession, order_id: int, data: OrderUpdate) -> Order:
    order = await order_repo.get(session, id=order_id)
    if not order:
        raise NotFoundException(f"Order with id {order_id} not found")

    if data.status is not None:
        _validate_status_transition(order.status, data.status)
        order.status = data.status.value
        await session.commit()
        await session.refresh(order)

        event_type = None
        if data.status == OrderStatus.CONFIRMED:
            event_type = ORDER_CONFIRMED
        elif data.status == OrderStatus.SHIPPED:
            event_type = ORDER_SHIPPED
        elif data.status == OrderStatus.CANCELLED:
            event_type = ORDER_CANCELLED

        if event_type:
            eventbus.publish(Event(event_type=event_type, data={"order_id": order_id, "user_id": order.user_id}))

    return order


async def delete_order(session: AsyncSession, order_id: int) -> Order:
    order = await order_repo.get(session, id=order_id)
    if not order:
        raise NotFoundException(f"Order with id {order_id} not found")
    return await order_repo.delete(session, id=order_id)
