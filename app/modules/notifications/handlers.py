import logging
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.eventbus import Event
from app.modules.notifications.channels import CHANNEL_REGISTRY
from app.modules.notifications.models import Notification, NotificationTemplate
from app.modules.notifications.repository import template_repo

logger = logging.getLogger(__name__)


class NotificationHandler:
    """事件驱动的通知处理器"""

    async def handle_event(self, session: AsyncSession, event: Event) -> list[Notification]:
        """处理事件，发送通知到所有渠道"""
        notifications = []
        user_id = event.data.get("user_id")
        if not user_id:
            logger.warning(f"Event {event.event_type} missing user_id")
            return notifications

        for channel_name, channel in CHANNEL_REGISTRY.items():
            notification = await self._send_to_channel(session, event, channel_name, channel, user_id)
            if notification:
                notifications.append(notification)

        return notifications

    async def _send_to_channel(
        self,
        session: AsyncSession,
        event: Event,
        channel_name: str,
        channel,
        user_id: int,
    ) -> Optional[Notification]:
        """发送到单个渠道"""
        template = await template_repo.get_by_name(session, event.event_type, channel_name)
        if not template:
            logger.debug(f"No template for {event.event_type}/{channel_name}")
            return None

        if not template.is_active:
            return None

        subject = self._render(template.subject, event.data) if template.subject else None
        body = self._render(template.body, event.data)

        notification = Notification(
            user_id=user_id,
            template_name=event.event_type,
            channel=channel_name,
            status="pending",
            subject=subject,
            body=body,
        )
        session.add(notification)
        await session.flush()

        try:
            success, error = await channel.send(user_id, subject, body)
            notification.status = "sent" if success else "failed"
            notification.sent_at = datetime.now(UTC) if success else None
            notification.error_message = error
        except Exception as e:
            logger.exception(f"Failed to send notification via {channel_name}")
            notification.status = "failed"
            notification.error_message = str(e)

        await session.commit()
        await session.refresh(notification)
        return notification

    def _render(self, template: Optional[str], context: dict) -> str:
        """简单模板渲染"""
        if not template:
            return ""
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result


notification_handler = NotificationHandler()
