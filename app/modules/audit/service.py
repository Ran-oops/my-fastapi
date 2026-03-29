from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.audit.repository import audit_log_repo
from app.modules.audit.schemas import AuditLogCreate


async def get_audit_log_by_id(session: AsyncSession, log_id: int) -> AuditLog | None:
    return await audit_log_repo.get(session, id=log_id)


async def get_audit_logs(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[AuditLog]:
    return await audit_log_repo.get_multi(session, skip=skip, limit=limit)


async def get_audit_logs_by_user(
    session: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
) -> list[AuditLog]:
    return await audit_log_repo.get_by_user(session, user_id, skip=skip, limit=limit)


async def get_audit_logs_by_resource(
    session: AsyncSession, resource_type: str, resource_id: int, skip: int = 0, limit: int = 100
) -> list[AuditLog]:
    return await audit_log_repo.get_by_resource(session, resource_type, resource_id, skip=skip, limit=limit)


async def get_audit_logs_count(session: AsyncSession) -> int:
    return await audit_log_repo.count(session)


async def get_audit_logs_count_by_user(session: AsyncSession, user_id: int) -> int:
    return await audit_log_repo.count_by_user(session, user_id)


async def get_audit_logs_count_by_resource(session: AsyncSession, resource_type: str, resource_id: int) -> int:
    return await audit_log_repo.count_by_resource(session, resource_type, resource_id)


async def create_audit_log(session: AsyncSession, data: AuditLogCreate) -> AuditLog:
    return await audit_log_repo.create(session, data=data)
