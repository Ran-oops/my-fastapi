import pytest
import pytest_asyncio

from app.modules.audit import service as audit_service
from app.modules.audit.schemas import AuditLogCreate


@pytest_asyncio.fixture
async def test_audit_log(session):
    audit_in = AuditLogCreate(
        user_id=1,
        action="create",
        resource_type="product",
        resource_id=1,
        old_value=None,
        new_value='{"name": "Test Product"}',
        ip_address="127.0.0.1",
    )
    return await audit_service.create_audit_log(session, audit_in)


@pytest_asyncio.fixture
async def multiple_audit_logs(session):
    logs = []
    actions = ["create", "update", "delete", "create", "update"]
    for i in range(5):
        audit_in = AuditLogCreate(
            user_id=i + 1,
            action=actions[i],
            resource_type="product" if i % 2 == 0 else "order",
            resource_id=i + 1,
            old_value='{"old": "value"}' if i % 2 == 1 else None,
            new_value=f'{{"new": "value{i}"}}',
            ip_address=f"192.168.1.{i}",
        )
        log = await audit_service.create_audit_log(session, audit_in)
        logs.append(log)
    return logs


@pytest_asyncio.fixture
async def superuser_headers(superuser_token):
    return {"Authorization": f"Bearer {superuser_token}"}


@pytest_asyncio.fixture
async def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}
