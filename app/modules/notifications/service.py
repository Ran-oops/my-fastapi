from sqlalchemy.ext.asyncio import AsyncSession

from app.core.eventbus import Event, eventbus
from app.modules.notifications.models import Notification, NotificationTemplate
from app.modules.notifications.repository import notification_repo, template_repo
from app.modules.notifications.schemas import (
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
)


async def get_notifications(
    session: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    is_read: bool | None = None,
    status: str | None = None,
) -> list[Notification]:
    """获取用户通知列表"""
    return await notification_repo.get_by_user(session, user_id, skip, limit, is_read, status)


async def get_notification_count(
    session: AsyncSession,
    user_id: int,
    is_read: bool | None = None,
    status: str | None = None,
) -> int:
    """获取用户通知数量"""
    return await notification_repo.count_by_user(session, user_id, is_read, status)


async def get_notification_by_id(session: AsyncSession, notification_id: int, user_id: int) -> Notification | None:
    """获取单条通知"""
    return await notification_repo.get(session, id=notification_id)


async def mark_notification_read(session: AsyncSession, notification_id: int, user_id: int) -> Notification | None:
    """标记单条已读"""
    return await notification_repo.mark_read(session, notification_id, user_id)


async def mark_all_read(session: AsyncSession, user_id: int) -> int:
    """标记全部已读"""
    return await notification_repo.mark_all_read(session, user_id)


async def create_template(session: AsyncSession, data: NotificationTemplateCreate) -> NotificationTemplate:
    """创建通知模板"""
    return await template_repo.create(session, data=data)


async def update_template(
    session: AsyncSession, template_id: int, data: NotificationTemplateUpdate
) -> NotificationTemplate:
    """更新通知模板"""
    template = await template_repo.get(session, id=template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")
    return await template_repo.update(session, instance=template, data=data)


async def delete_template(session: AsyncSession, template_id: int) -> NotificationTemplate:
    """删除通知模板"""
    return await template_repo.delete(session, id=template_id)


async def get_templates(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[NotificationTemplate]:
    """获取模板列表"""
    return await template_repo.get_multi(session, skip=skip, limit=limit)


async def publish_event(event_type: str, data: dict) -> None:
    """发布事件（供业务模块调用）"""
    event = Event(event_type=event_type, data=data)
    eventbus.publish(event)
