from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repository import BaseRepository
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderUpdate


class OrderRepository(BaseRepository[Order, OrderCreate, OrderUpdate]):
    async def get_with_items(self, session: AsyncSession, order_id: int) -> Order | None:
        result = await session.execute(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def get_by_user(self, session: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> list[Order]:
        result = await session.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_status(
        self, session: AsyncSession, status: OrderStatus, skip: int = 0, limit: int = 100
    ) -> list[Order]:
        result = await session.execute(
            select(Order).where(Order.status == status.value).order_by(Order.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())


order_repo = OrderRepository(Order)
