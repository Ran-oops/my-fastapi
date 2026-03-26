import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit import service as audit_service
from app.modules.audit.schemas import AuditLogCreate


class TestAuditServiceCreate:
    async def test_create_audit_log_success(self, session: AsyncSession):
        audit_in = AuditLogCreate(
            user_id=1,
            action="create",
            resource_type="product",
            resource_id=1,
            old_value=None,
            new_value='{"name": "Test Product"}',
            ip_address="127.0.0.1",
        )
        result = await audit_service.create_audit_log(session, audit_in)
        assert result.id is not None
        assert result.user_id == 1
        assert result.action == "create"
        assert result.resource_type == "product"
        assert result.resource_id == 1
        assert result.old_value is None
        assert result.new_value == '{"name": "Test Product"}'
        assert result.ip_address == "127.0.0.1"

    async def test_create_audit_log_without_user_id(self, session: AsyncSession):
        audit_in = AuditLogCreate(
            user_id=None,
            action="system_refresh",
            resource_type="cache",
            resource_id=0,
            ip_address=None,
        )
        result = await audit_service.create_audit_log(session, audit_in)
        assert result.id is not None
        assert result.user_id is None
        assert result.action == "system_refresh"
        assert result.resource_type == "cache"
        assert result.resource_id == 0
        assert result.ip_address is None

    async def test_create_audit_log_minimal(self, session: AsyncSession):
        audit_in = AuditLogCreate(
            action="login",
            resource_type="session",
            resource_id=1,
        )
        result = await audit_service.create_audit_log(session, audit_in)
        assert result.id is not None
        assert result.user_id is None
        assert result.action == "login"
        assert result.resource_type == "session"
        assert result.resource_id == 1
        assert result.old_value is None
        assert result.new_value is None
        assert result.ip_address is None


class TestAuditServiceGet:
    async def test_get_audit_log_by_id_found(self, session: AsyncSession, test_audit_log):
        result = await audit_service.get_audit_log_by_id(session, test_audit_log.id)
        assert result is not None
        assert result.id == test_audit_log.id
        assert result.action == test_audit_log.action

    async def test_get_audit_log_by_id_not_found(self, session: AsyncSession):
        result = await audit_service.get_audit_log_by_id(session, 99999)
        assert result is None


class TestAuditServiceList:
    async def test_get_audit_logs_pagination(self, session: AsyncSession, multiple_audit_logs):
        page1 = await audit_service.get_audit_logs(session, skip=0, limit=2)
        page2 = await audit_service.get_audit_logs(session, skip=2, limit=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    async def test_get_audit_logs_by_user(self, session: AsyncSession):
        for i in range(3):
            audit_in = AuditLogCreate(
                user_id=42,
                action="update",
                resource_type="user",
                resource_id=i + 1,
            )
            await audit_service.create_audit_log(session, audit_in)
        audit_in = AuditLogCreate(
            user_id=99,
            action="delete",
            resource_type="user",
            resource_id=100,
        )
        await audit_service.create_audit_log(session, audit_in)
        results = await audit_service.get_audit_logs_by_user(session, 42)
        assert len(results) == 3
        for log in results:
            assert log.user_id == 42

    async def test_get_audit_logs_by_resource(self, session: AsyncSession):
        for i in range(3):
            audit_in = AuditLogCreate(
                user_id=1,
                action="create",
                resource_type="order",
                resource_id=500,
            )
            await audit_service.create_audit_log(session, audit_in)
        audit_in = AuditLogCreate(
            user_id=1,
            action="create",
            resource_type="order",
            resource_id=501,
        )
        await audit_service.create_audit_log(session, audit_in)
        results = await audit_service.get_audit_logs_by_resource(session, "order", 500)
        assert len(results) == 3
        for log in results:
            assert log.resource_type == "order"
            assert log.resource_id == 500

    async def test_get_audit_logs_count(self, session: AsyncSession, multiple_audit_logs):
        count = await audit_service.get_audit_logs_count(session)
        assert count >= 5
