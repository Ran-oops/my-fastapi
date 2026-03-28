from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import BaseRepository
from app.modules.notifications.models import Notification, NotificationTemplate
from app.modules.notifications.schemas import NotificationTemplateCreate, NotificationTemplateUpdate


class NotificationRepository(BaseRepository[Notification, NotificationTemplateCreate, NotificationTemplateUpdate]):
    """通知仓库"""

    def __init__(self):
        super().__init__(Notification)

    async def get_by_user(
        self,
        session: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        is_read: bool | None = None,
        status: str | None = None,
    ) -> list[Notification]:
        """获取用户通知列表"""
        conditions = [Notification.user_id == user_id]
        if is_read is not None:
            conditions.append(Notification.is_read == is_read)
        if status is not None:
            conditions.append(Notification.status == status)

        stmt = (
            select(Notification)
            .where(and_(*conditions))
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        session: AsyncSession,
        user_id: int,
        is_read: bool | None = None,
        status: str | None = None,
    ) -> int:
        """统计用户通知数量"""
        from sqlalchemy import func

        conditions = [Notification.user_id == user_id]
        if is_read is not None:
            conditions.append(Notification.is_read == is_read)
        if status is not None:
            conditions.append(Notification.status == status)

        stmt = select(func.count(Notification.id)).where(and_(*conditions))
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def mark_read(self, session: AsyncSession, notification_id: int, user_id: int) -> Notification | None:
        """标记单条已读"""
        stmt = select(Notification).where(and_(Notification.id == notification_id, Notification.user_id == user_id))
        result = await session.execute(stmt)
        notification = result.scalar_one_or_none()
        if notification:
            notification.is_read = True
            await session.commit()
            await session.refresh(notification)
        return notification

    async def mark_all_read(self, session: AsyncSession, user_id: int) -> int:
        """标记全部已读 - 使用批量更新"""
        stmt = (
            update(Notification)
            .where(and_(Notification.user_id == user_id, Notification.is_read == False))
            .values(is_read=True)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount


class NotificationTemplateRepository(
    BaseRepository[NotificationTemplate, NotificationTemplateCreate, NotificationTemplateUpdate]
):
    """通知模板仓库"""

    def __init__(self):
        super().__init__(NotificationTemplate)

    async def get_by_name(self, session: AsyncSession, name: str, channel: str) -> NotificationTemplate | None:
        """根据名称和渠道获取模板"""
        stmt = select(NotificationTemplate).where(
            and_(
                NotificationTemplate.name == name,
                NotificationTemplate.channel == channel,
                NotificationTemplate.is_active == True,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


notification_repo = NotificationRepository()
template_repo = NotificationTemplateRepository()
