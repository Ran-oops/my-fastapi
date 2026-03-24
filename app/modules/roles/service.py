from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.roles.models import Permission, Role
from app.modules.roles.repository import permission_repository, role_repository
from app.modules.roles.schemas import PermissionCreate, PermissionUpdate, RoleCreate, RoleUpdate
from app.modules.users.repository import user_repository


class RoleService:
    @staticmethod
    async def create_role(db: AsyncSession, role_in: RoleCreate) -> Role:
        existing = await role_repository.get_by_name(db, name=role_in.name)
        if existing:
            raise ConflictException(f"Role with name '{role_in.name}' already exists")
        return await role_repository.create(db, obj_in=role_in)

    @staticmethod
    async def update_role(db: AsyncSession, role_id: int, role_in: RoleUpdate) -> Role:
        role = await role_repository.get(db, id=role_id)
        if not role:
            raise NotFoundException(f"Role with id {role_id} not found")
        if role_in.name and role_in.name != role.name:
            existing = await role_repository.get_by_name(db, name=role_in.name)
            if existing:
                raise ConflictException(f"Role with name '{role_in.name}' already exists")
        return await role_repository.update(db, db_obj=role, obj_in=role_in)

    @staticmethod
    async def delete_role(db: AsyncSession, role_id: int) -> Role:
        role = await role_repository.get(db, id=role_id)
        if not role:
            raise NotFoundException(f"Role with id {role_id} not found")
        users = await role_repository.get_users(db, role_id=role_id)
        if users:
            raise ConflictException(f"Cannot delete role with {len(users)} assigned users")
        return await role_repository.delete(db, id=role_id)

    @staticmethod
    async def get_role_by_id(db: AsyncSession, role_id: int) -> Role | None:
        return await role_repository.get_with_permissions(db, role_id=role_id)

    @staticmethod
    async def get_roles(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Role]:
        return await role_repository.get_multi_with_permissions(db, skip=skip, limit=limit)

    @staticmethod
    async def assign_role_to_user(db: AsyncSession, user_id: int, role_id: int):
        user = await user_repository.get_with_roles(db, user_id=user_id)
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        role = await role_repository.get(db, id=role_id)
        if not role:
            raise NotFoundException(f"Role with id {role_id} not found")
        if role not in user.roles:
            user.roles.append(role)
            await db.commit()
            await db.refresh(user)
        return user

    @staticmethod
    async def remove_role_from_user(db: AsyncSession, user_id: int, role_id: int):
        user = await user_repository.get_with_roles(db, user_id=user_id)
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        role = await role_repository.get(db, id=role_id)
        if not role:
            raise NotFoundException(f"Role with id {role_id} not found")
        if role in user.roles:
            user.roles.remove(role)
            await db.commit()
            await db.refresh(user)
        return user

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: int) -> list[Role]:
        user = await user_repository.get_with_roles(db, user_id=user_id)
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        return list(user.roles)

    @staticmethod
    async def check_user_permission(db: AsyncSession, user_id: int, permission_code: str) -> bool:
        user = await user_repository.get_with_roles(db, user_id=user_id)
        if not user:
            return False
        for role in user.roles:
            permissions = await permission_repository.get_by_role(db, role_id=role.id)
            for perm in permissions:
                if perm.code == permission_code:
                    return True
        return False


class PermissionService:
    @staticmethod
    async def create_permission(db: AsyncSession, permission_in: PermissionCreate) -> Permission:
        existing = await permission_repository.get_by_code(db, code=permission_in.code)
        if existing:
            raise ConflictException(f"Permission with code '{permission_in.code}' already exists")
        return await permission_repository.create(db, obj_in=permission_in)

    @staticmethod
    async def update_permission(db: AsyncSession, permission_id: int, permission_in: PermissionUpdate) -> Permission:
        permission_obj = await permission_repository.get(db, id=permission_id)
        if not permission_obj:
            raise NotFoundException(f"Permission with id {permission_id} not found")
        return await permission_repository.update(db, db_obj=permission_obj, obj_in=permission_in)

    @staticmethod
    async def delete_permission(db: AsyncSession, permission_id: int) -> Permission:
        permission_obj = await permission_repository.get(db, id=permission_id)
        if not permission_obj:
            raise NotFoundException(f"Permission with id {permission_id} not found")
        roles = await permission_repository.get_roles(db, permission_id=permission_id)
        if roles:
            raise ConflictException(f"Cannot delete permission assigned to {len(roles)} roles")
        return await permission_repository.delete(db, id=permission_id)

    @staticmethod
    async def get_permission_by_id(db: AsyncSession, permission_id: int) -> Permission | None:
        return await permission_repository.get(db, id=permission_id)

    @staticmethod
    async def get_permissions(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Permission]:
        return await permission_repository.get_multi(db, skip=skip, limit=limit)

    @staticmethod
    async def get_role_permissions(db: AsyncSession, role_id: int) -> list[Permission]:
        return await permission_repository.get_by_role(db, role_id=role_id)


role_service = RoleService()
permission_service = PermissionService()
