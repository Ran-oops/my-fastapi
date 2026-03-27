import pytest

from app.modules.notifications import service as notification_service
from app.modules.notifications.schemas import NotificationTemplateCreate


@pytest.mark.asyncio
class TestNotificationService:
    async def test_create_template(self, session):
        data = NotificationTemplateCreate(
            name="order.confirmed",
            channel="in_app",
            subject="Order Confirmed",
            body="Your order #{{order_id}} is confirmed",
        )
        template = await notification_service.create_template(session, data)
        assert template.id is not None
        assert template.name == "order.confirmed"
        assert template.channel == "in_app"

    async def test_get_templates(self, session, test_template):
        templates = await notification_service.get_templates(session)
        assert len(templates) >= 1
        assert any(t.name.startswith("test.event") for t in templates)

    async def test_create_and_get_notification(self, session, test_template):
        from app.modules.notifications.models import Notification

        notification = Notification(
            user_id=1,
            template_name=test_template.name,
            channel="in_app",
            status="sent",
            subject="Test",
            body="Test body",
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)

        notifications = await notification_service.get_notifications(session, user_id=1)
        assert len(notifications) >= 1
        assert notifications[0].template_name == test_template.name
