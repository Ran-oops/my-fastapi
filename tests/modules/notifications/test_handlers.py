import pytest
from unittest.mock import AsyncMock, patch

from app.modules.notifications.handlers import NotificationHandler
from app.modules.notifications.models import NotificationTemplate, Notification
from app.core.eventbus import Event
from app.core.events import ORDER_CONFIRMED


@pytest.mark.asyncio
class TestNotificationHandler:
    async def test_handle_event_creates_notification(self, session):
        handler = NotificationHandler()

        template = NotificationTemplate(
            name=ORDER_CONFIRMED,
            channel="in_app",
            subject="Order Confirmed",
            body="Your order #{{order_id}} is confirmed",
            is_active=True,
        )
        session.add(template)
        await session.commit()

        event = Event(event_type=ORDER_CONFIRMED, data={"order_id": 123, "user_id": 1})

        notifications = await handler.handle_event(session, event)

        assert len(notifications) >= 1
        assert notifications[0].user_id == 1
        assert notifications[0].status == "sent"

    async def test_handle_event_without_user_id(self, session):
        handler = NotificationHandler()

        event = Event(event_type=ORDER_CONFIRMED, data={"order_id": 123})

        notifications = await handler.handle_event(session, event)

        assert len(notifications) == 0

    async def test_handle_event_template_rendering(self, session):
        handler = NotificationHandler()

        template = NotificationTemplate(
            name="test.render",
            channel="in_app",
            subject="Hello {{name}}",
            body="Your order #{{order_id}} is ready",
            is_active=True,
        )
        session.add(template)
        await session.commit()

        event = Event(event_type="test.render", data={"order_id": 456, "user_id": 2, "name": "John"})

        notifications = await handler.handle_event(session, event)

        assert len(notifications) >= 1
        assert "456" in notifications[0].body
        assert "John" in notifications[0].subject

    async def test_handle_event_inactive_template_skipped(self, session):
        handler = NotificationHandler()

        template = NotificationTemplate(
            name="test.inactive",
            channel="in_app",
            subject="Test",
            body="Test body",
            is_active=False,
        )
        session.add(template)
        await session.commit()

        event = Event(event_type="test.inactive", data={"user_id": 1})

        notifications = await handler.handle_event(session, event)

        assert len(notifications) == 0

    async def test_render_with_missing_variable(self):
        handler = NotificationHandler()

        result = handler._render("Hello {{name}}, order #{{order_id}}", {"name": "John"})

        assert result == "Hello John, order #{{order_id}}"

    async def test_render_with_none_template(self):
        handler = NotificationHandler()

        result = handler._render(None, {"key": "value"})

        assert result == ""
