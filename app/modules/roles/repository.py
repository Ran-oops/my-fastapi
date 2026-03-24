from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.shared.base import CRUDBase
from app.modules.roles.models import Permission, Role, role_permissions, user_roles
from app.modules.roles.schemas import PermissionCreate, PermissionUpdate, RoleCreate, RoleUpdate


class RoleRepository(CRUDBase[Role, RoleCreate, RoleUpdate]):
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


class PermissionRepository(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
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


role_repository = RoleRepository(Role)
permission_repository = PermissionRepository(Permission)
