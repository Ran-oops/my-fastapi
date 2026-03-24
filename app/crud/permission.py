from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.user import Permission, role_permissions
from app.schemas.permission import PermissionCreate, PermissionUpdate


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    async def get_by_code(self, db: AsyncSession, code: str) -> Permission | None:
        result = await db.execute(select(Permission).where(Permission.code == code))
        return result.scalar_one_or_none()

    async def get_by_role(self, db: AsyncSession, role_id: int) -> list[Permission]:
        result = await db.execute(
            select(Permission)
            .join(role_permissions)
            .where(role_permissions.c.role_id == role_id)
            .order_by(Permission.id)
        )
        return list(result.scalars().all())

    async def get_roles(self, db: AsyncSession, permission_id: int) -> list[int]:
        result = await db.execute(
            select(role_permissions.c.role_id).where(role_permissions.c.permission_id == permission_id)
        )
        return [row[0] for row in result.fetchall()]


permission = CRUDPermission(Permission)
