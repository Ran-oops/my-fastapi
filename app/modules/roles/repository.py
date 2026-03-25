from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repository import BaseRepository
from app.modules.roles.associations import role_permissions
from app.modules.roles.models import Permission, Role
from app.modules.roles.schemas import PermissionCreate, PermissionUpdate, RoleCreate, RoleUpdate
from app.modules.users.associations import user_roles


class RoleRepository(BaseRepository[Role, RoleCreate, RoleUpdate]):
    async def get_by_name(self, session: AsyncSession, name: str) -> Role | None:
        result = await session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_with_permissions(self, session: AsyncSession, role_id: int) -> Role | None:
        result = await session.execute(select(Role).where(Role.id == role_id).options(selectinload(Role.permissions)))
        return result.scalar_one_or_none()

    async def get_multi_with_permissions(self, session: AsyncSession, skip: int = 0, limit: int = 100) -> list[Role]:
        result = await session.execute(
            select(Role).options(selectinload(Role.permissions)).order_by(Role.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def add_permission(self, session: AsyncSession, role_id: int, permission_id: int) -> Role | None:
        role = await self.get_with_permissions(session, role_id)
        if not role:
            return None
        permission = await session.execute(select(Permission).where(Permission.id == permission_id))
        permission_obj = permission.scalar_one_or_none()
        if not permission_obj:
            return None
        if permission_obj not in role.permissions:
            role.permissions.append(permission_obj)
            await session.commit()
            await session.refresh(role)
        return role

    async def remove_permission(self, session: AsyncSession, role_id: int, permission_id: int) -> Role | None:
        role = await self.get_with_permissions(session, role_id)
        if not role:
            return None
        permission = await session.execute(select(Permission).where(Permission.id == permission_id))
        permission_obj = permission.scalar_one_or_none()
        if not permission_obj:
            return None
        if permission_obj in role.permissions:
            role.permissions.remove(permission_obj)
            await session.commit()
            await session.refresh(role)
        return role

    async def get_users(self, session: AsyncSession, role_id: int) -> list[int]:
        result = await session.execute(select(user_roles.c.user_id).where(user_roles.c.role_id == role_id))
        return [row[0] for row in result.fetchall()]


class PermissionRepository(BaseRepository[Permission, PermissionCreate, PermissionUpdate]):
    async def get_by_code(self, session: AsyncSession, code: str) -> Permission | None:
        result = await session.execute(select(Permission).where(Permission.code == code))
        return result.scalar_one_or_none()

    async def get_by_role(self, session: AsyncSession, role_id: int) -> list[Permission]:
        result = await session.execute(
            select(Permission)
            .join(role_permissions)
            .where(role_permissions.c.role_id == role_id)
            .order_by(Permission.id)
        )
        return list(result.scalars().all())

    async def get_roles(self, session: AsyncSession, permission_id: int) -> list[int]:
        result = await session.execute(
            select(role_permissions.c.role_id).where(role_permissions.c.permission_id == permission_id)
        )
        return [row[0] for row in result.fetchall()]


role_repo = RoleRepository(Role)
permission_repo = PermissionRepository(Permission)
