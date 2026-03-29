from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.roles.models import Permission, Role
from app.modules.roles.repository import permission_repo, role_repo
from app.modules.roles.schemas import PermissionCreate, PermissionUpdate, RoleCreate, RoleUpdate
from app.modules.users.repository import user_repo


async def create_role(session: AsyncSession, data: RoleCreate) -> Role:
    existing = await role_repo.get_by_name(session, name=data.name)
    if existing:
        raise ConflictException(f"Role with name '{data.name}' already exists")
    return await role_repo.create(session, data=data)


async def update_role(session: AsyncSession, role_id: int, data: RoleUpdate) -> Role:
    role = await role_repo.get(session, id=role_id)
    if not role:
        raise NotFoundException(f"Role with id {role_id} not found")
    if data.name and data.name != role.name:
        existing = await role_repo.get_by_name(session, name=data.name)
        if existing:
            raise ConflictException(f"Role with name '{data.name}' already exists")
    return await role_repo.update(session, instance=role, data=data)


async def delete_role(session: AsyncSession, role_id: int) -> Role:
    role = await role_repo.get(session, id=role_id)
    if not role:
        raise NotFoundException(f"Role with id {role_id} not found")
    users = await role_repo.get_users(session, role_id=role_id)
    if users:
        raise ConflictException(f"Cannot delete role with {len(users)} assigned users")
    return await role_repo.delete(session, id=role_id)


async def get_role_by_id(session: AsyncSession, role_id: int) -> Role | None:
    return await role_repo.get_with_permissions(session, role_id=role_id)


async def get_roles(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[Role]:
    return await role_repo.get_multi_with_permissions(session, skip=skip, limit=limit)


async def get_roles_count(session: AsyncSession) -> int:
    return await role_repo.count(session)


async def assign_role_to_user(session: AsyncSession, user_id: int, role_id: int):
    user = await user_repo.get_with_roles(session, user_id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    role = await role_repo.get(session, id=role_id)
    if not role:
        raise NotFoundException(f"Role with id {role_id} not found")
    if role not in user.roles:
        user.roles.append(role)
        await session.commit()
        await session.refresh(user)
    return user


async def remove_role_from_user(session: AsyncSession, user_id: int, role_id: int):
    user = await user_repo.get_with_roles(session, user_id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    role = await role_repo.get(session, id=role_id)
    if not role:
        raise NotFoundException(f"Role with id {role_id} not found")
    if role in user.roles:
        user.roles.remove(role)
        await session.commit()
        await session.refresh(user)
    return user


async def get_user_roles(session: AsyncSession, user_id: int) -> list[Role]:
    user = await user_repo.get_with_roles(session, user_id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    return list(user.roles)


async def check_user_permission(session: AsyncSession, user_id: int, permission_code: str) -> bool:
    user = await user_repo.get_with_roles(session, user_id=user_id)
    if not user:
        return False
    for role in user.roles:
        permissions = await permission_repo.get_by_role(session, role_id=role.id)
        for perm in permissions:
            if perm.code == permission_code:
                return True
    return False


async def create_permission(session: AsyncSession, data: PermissionCreate) -> Permission:
    existing = await permission_repo.get_by_code(session, code=data.code)
    if existing:
        raise ConflictException(f"Permission with code '{data.code}' already exists")
    return await permission_repo.create(session, data=data)


async def update_permission(session: AsyncSession, permission_id: int, data: PermissionUpdate) -> Permission:
    permission_obj = await permission_repo.get(session, id=permission_id)
    if not permission_obj:
        raise NotFoundException(f"Permission with id {permission_id} not found")
    return await permission_repo.update(session, instance=permission_obj, data=data)


async def delete_permission(session: AsyncSession, permission_id: int) -> Permission:
    permission_obj = await permission_repo.get(session, id=permission_id)
    if not permission_obj:
        raise NotFoundException(f"Permission with id {permission_id} not found")
    roles = await permission_repo.get_roles(session, permission_id=permission_id)
    if roles:
        raise ConflictException(f"Cannot delete permission assigned to {len(roles)} roles")
    return await permission_repo.delete(session, id=permission_id)


async def get_permission_by_id(session: AsyncSession, permission_id: int) -> Permission | None:
    return await permission_repo.get(session, id=permission_id)


async def get_permissions(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[Permission]:
    return await permission_repo.get_multi(session, skip=skip, limit=limit)


async def get_permissions_count(session: AsyncSession) -> int:
    return await permission_repo.count(session)


async def get_role_permissions(session: AsyncSession, role_id: int) -> list[Permission]:
    return await permission_repo.get_by_role(session, role_id=role_id)
