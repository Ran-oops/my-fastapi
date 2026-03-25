from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import BaseRepository
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogCreate


class AuditLogRepository(BaseRepository[AuditLog, AuditLogCreate, AuditLogCreate]):
    async def get_by_user(self, session: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        result = await session.execute(
            select(AuditLog).where(AuditLog.user_id == user_id).order_by(AuditLog.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_resource(
        self, session: AsyncSession, resource_type: str, resource_id: int, skip: int = 0, limit: int = 100
    ) -> list[AuditLog]:
        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.resource_type == resource_type, AuditLog.resource_id == resource_id)
            .order_by(AuditLog.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


audit_log_repo = AuditLogRepository(AuditLog)
