import pytest_asyncio

from app.core.eventbus import eventbus
from tests.helpers import make_notification, make_template


@pytest_asyncio.fixture
async def test_template(session):
    """Create a test notification template."""
    template = make_template()
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@pytest_asyncio.fixture
async def test_email_template(session):
    """Create a test email template."""
    template = make_template(
        channel="email",
        subject="Email for {{user_id}}",
        body="Email body: {{message}}",
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@pytest_asyncio.fixture(autouse=True)
def clear_eventbus():
    """Clear eventbus before and after each test."""
    eventbus.clear()
    yield
    eventbus.clear()


@pytest_asyncio.fixture
async def test_notification(session, test_user):
    """Create a test notification."""
    notification = make_notification(user_id=test_user.id)
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification


@pytest_asyncio.fixture
async def multiple_notifications(session, test_user):
    """Create multiple test notifications for the test user."""
    notifications = []
    for i in range(5):
        notification = make_notification(
            user_id=test_user.id,
            channel="in_app" if i % 2 == 0 else "email",
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
