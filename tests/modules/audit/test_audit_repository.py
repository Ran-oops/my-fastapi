import pytest

from app.modules.audit.repository import audit_log_repo
from app.modules.audit.schemas import AuditLogCreate
from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestAuditLogRepositoryGetByUser:
    async def test_get_by_user_returns_matching_logs(self, session, test_user, multiple_audit_logs):
        logs = await audit_log_repo.get_by_user(session, user_id=test_user.id)
        assert len(logs) >= 1
        assert all(log.user_id == test_user.id for log in logs)

    async def test_get_by_user_empty(self, session, multiple_audit_logs):
        logs = await audit_log_repo.get_by_user(session, user_id=NONEXISTENT_ID)
        assert len(logs) == 0


@pytest.mark.asyncio
class TestAuditLogRepositoryGetByResource:
    async def test_get_by_resource_returns_matching_logs(self, session, multiple_audit_logs):
        logs = await audit_log_repo.get_by_resource(session, resource_type="product", resource_id=1)
        assert len(logs) >= 1
        assert all(log.resource_type == "product" and log.resource_id == 1 for log in logs)

    async def test_get_by_resource_empty(self, session, multiple_audit_logs):
        logs = await audit_log_repo.get_by_resource(session, resource_type="nonexistent", resource_id=NONEXISTENT_ID)
        assert len(logs) == 0


@pytest.mark.asyncio
class TestAuditLogRepositoryGet:
    async def test_get_found(self, session, test_audit_log):
        log = await audit_log_repo.get(session, id=test_audit_log.id)
        assert log is not None
        assert log.id == test_audit_log.id

    async def test_get_not_found(self, session):
        log = await audit_log_repo.get(session, id=NONEXISTENT_ID)
        assert log is None


@pytest.mark.asyncio
class TestAuditLogRepositoryCreate:
    async def test_create_audit_log(self, session):
        log_in = AuditLogCreate(
            user_id=12345,
            action="create",
            resource_type="order",
            resource_id=100,
            old_value=None,
            new_value='{"status": "pending"}',
            ip_address="10.0.0.1",
        )
        log = await audit_log_repo.create(session, log_in)
        assert log.id is not None
        assert log.user_id == 12345
        assert log.action == "create"
        assert log.resource_type == "order"
        assert log.resource_id == 100


@pytest.mark.asyncio
class TestAuditLogRepositoryMulti:
    async def test_get_multi(self, session, multiple_audit_logs):
        logs = await audit_log_repo.get_multi(session, skip=0, limit=10)
        assert len(logs) >= 5

    async def test_count(self, session, multiple_audit_logs):
        count = await audit_log_repo.count(session)
        assert count >= 5
