from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.user import Permission, Role, user_roles
from app.schemas.role import RoleCreate, RoleUpdate


class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    async def get_by_name(self, db: AsyncSession, name: str) -> Role | None:
        result = await db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_with_permissions(self, db: AsyncSession, role_id: int) -> Role | None:
        result = await db.execute(select(Role).where(Role.id == role_id).options(selectinload(Role.permissions)))
        return result.scalar_one_or_none()

    async def get_multi_with_permissions(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Role]:
        result = await db.execute(
            select(Role).options(selectinload(Role.permissions)).order_by(Role.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def add_permission(self, db: AsyncSession, role_id: int, permission_id: int) -> Role | None:
        role = await self.get_with_permissions(db, role_id)
        if not role:
            return None
        permission = await db.execute(select(Permission).where(Permission.id == permission_id))
        permission_obj = permission.scalar_one_or_none()
        if not permission_obj:
            return None
        if permission_obj not in role.permissions:
            role.permissions.append(permission_obj)
            await db.commit()
            await db.refresh(role)
        return role

    async def remove_permission(self, db: AsyncSession, role_id: int, permission_id: int) -> Role | None:
        role = await self.get_with_permissions(db, role_id)
        if not role:
            return None
        permission = await db.execute(select(Permission).where(Permission.id == permission_id))
        permission_obj = permission.scalar_one_or_none()
        if not permission_obj:
            return None
        if permission_obj in role.permissions:
            role.permissions.remove(permission_obj)
            await db.commit()
            await db.refresh(role)
        return role

    async def get_users(self, db: AsyncSession, role_id: int) -> list[int]:
        result = await db.execute(select(user_roles.c.user_id).where(user_roles.c.role_id == role_id))
        return [row[0] for row in result.fetchall()]


role = CRUDRole(Role)
