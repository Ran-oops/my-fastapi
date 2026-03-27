import uuid

import pytest_asyncio

from app.core.eventbus import eventbus
from app.modules.notifications.models import NotificationTemplate


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
