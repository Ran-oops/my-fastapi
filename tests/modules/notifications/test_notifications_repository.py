import pytest

from app.modules.notifications.repository import notification_repo
from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestNotificationRepositoryGetByUser:
    async def test_get_by_user_returns_notifications(self, session, test_user, multiple_notifications):
        notifications = await notification_repo.get_by_user(session, user_id=test_user.id)
        assert len(notifications) >= 5
        assert all(n.user_id == test_user.id for n in notifications)

    async def test_get_by_user_empty(self, session, multiple_notifications):
        notifications = await notification_repo.get_by_user(session, user_id=NONEXISTENT_ID)
        assert len(notifications) == 0

    async def test_get_by_user_filter_by_read(self, session, test_user, multiple_notifications):
        read = await notification_repo.get_by_user(session, user_id=test_user.id, is_read=True)
        unread = await notification_repo.get_by_user(session, user_id=test_user.id, is_read=False)
        assert len(read) >= 2
        assert len(unread) >= 3
        assert all(n.is_read for n in read)
        assert all(not n.is_read for n in unread)


@pytest.mark.asyncio
class TestNotificationRepositoryCountByUser:
    async def test_count_by_user(self, session, test_user, multiple_notifications):
        count = await notification_repo.count_by_user(session, user_id=test_user.id)
        assert count >= 5

    async def test_count_by_user_empty(self, session, multiple_notifications):
        count = await notification_repo.count_by_user(session, user_id=NONEXISTENT_ID)
        assert count == 0


@pytest.mark.asyncio
class TestNotificationRepositoryMarkRead:
    async def test_mark_read_success(self, session, test_notification):
        assert test_notification.is_read is False
        result = await notification_repo.mark_read(session, test_notification.id, test_notification.user_id)
        assert result is not None
        assert result.is_read is True

    async def test_mark_read_not_found(self, session, test_user):
        result = await notification_repo.mark_read(session, NONEXISTENT_ID, test_user.id)
        assert result is None


@pytest.mark.asyncio
class TestNotificationRepositoryMarkAllRead:
    async def test_mark_all_read(self, session, test_user, multiple_notifications):
        updated = await notification_repo.mark_all_read(session, user_id=test_user.id)
        assert updated >= 3
        unread = await notification_repo.get_by_user(session, user_id=test_user.id, is_read=False)
        assert len(unread) == 0


@pytest.mark.asyncio
class TestNotificationRepositoryGet:
    async def test_get_found(self, session, test_notification):
        result = await notification_repo.get(session, id=test_notification.id)
        assert result is not None
        assert result.id == test_notification.id

    async def test_get_not_found(self, session):
        result = await notification_repo.get(session, id=NONEXISTENT_ID)
        assert result is None
