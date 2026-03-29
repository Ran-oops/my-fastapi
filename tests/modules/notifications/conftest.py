import uuid

import pytest_asyncio

from app.core.eventbus import eventbus
from app.modules.notifications.models import Notification, NotificationTemplate


@pytest_asyncio.fixture
async def test_template(session):
    """创建测试模板"""
    unique_name = f"test.event.{uuid.uuid4().hex[:8]}"
    template = NotificationTemplate(
        name=unique_name,
        channel="in_app",
        subject="Test Subject",
        body="Hello {{user_id}}, message: {{message}}",
        is_active=True,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@pytest_asyncio.fixture
async def test_email_template(session):
    """创建邮件测试模板"""
    unique_name = f"test.event.{uuid.uuid4().hex[:8]}"
    template = NotificationTemplate(
        name=unique_name,
        channel="email",
        subject="Email for {{user_id}}",
        body="Email body: {{message}}",
        is_active=True,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@pytest_asyncio.fixture(autouse=True)
def clear_eventbus():
    """每个测试前后清空事件总线"""
    eventbus.clear()
    yield
    eventbus.clear()


@pytest_asyncio.fixture
async def test_notification(session):
    """Create a test notification."""
    notification = Notification(
        user_id=1,
        template_name=f"test.notify.{uuid.uuid4().hex[:8]}",
        channel="in_app",
        status="sent",
        subject="Test Subject",
        body="Test notification body",
        is_read=False,
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification


@pytest_asyncio.fixture
async def multiple_notifications(session):
    """Create multiple test notifications for user 1."""
    notifications = []
    for i in range(5):
        notification = Notification(
            user_id=1,
            template_name=f"test.notify.{uuid.uuid4().hex[:8]}",
            channel="in_app" if i % 2 == 0 else "email",
            status="sent",
            subject=f"Subject {i}",
            body=f"Body {i}",
            is_read=i < 2,
        )
        session.add(notification)
        notifications.append(notification)
    await session.commit()
    for n in notifications:
        await session.refresh(n)
    return notifications
