from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.crud.permission import permission as permission_crud
from app.crud.role import role as role_crud
from app.crud.user import user as user_crud
from app.models.user import Role, User
from app.schemas.role import RoleCreate, RoleUpdate


class RoleService:
    @staticmethod
    async def create_role(db: AsyncSession, role_in: RoleCreate) -> Role:
        existing = await role_crud.get_by_name(db, name=role_in.name)
        if existing:
            raise ConflictException(f"Role with name '{role_in.name}' already exists")
        return await role_crud.create(db, obj_in=role_in)

    @staticmethod
    async def update_role(db: AsyncSession, role_id: int, role_in: RoleUpdate) -> Role:
        role = await role_crud.get(db, id=role_id)
        if not role:
            raise NotFoundException(f"Role with id {role_id} not found")
        if role_in.name and role_in.name != role.name:
            existing = await role_crud.get_by_name(db, name=role_in.name)
            if existing:
                raise ConflictException(f"Role with name '{role_in.name}' already exists")
        return await role_crud.update(db, db_obj=role, obj_in=role_in)

    @staticmethod
    async def delete_role(db: AsyncSession, role_id: int) -> Role:
        role = await role_crud.get(db, id=role_id)
        if not role:
            raise NotFoundException(f"Role with id {role_id} not found")
        users = await role_crud.get_users(db, role_id=role_id)
        if users:
            raise ConflictException(f"Cannot delete role with {len(users)} assigned users")
        return await role_crud.delete(db, id=role_id)

    @staticmethod
    async def get_role_by_id(db: AsyncSession, role_id: int) -> Role | None:
        return await role_crud.get_with_permissions(db, role_id=role_id)

    @staticmethod
    async def get_roles(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Role]:
        return await role_crud.get_multi_with_permissions(db, skip=skip, limit=limit)

    @staticmethod
    async def assign_role_to_user(db: AsyncSession, user_id: int, role_id: int) -> User:
        user = await user_crud.get_with_roles(db, user_id=user_id)
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        role = await role_crud.get(db, id=role_id)
        if not role:
            raise NotFoundException(f"Role with id {role_id} not found")
        if role not in user.roles:
            user.roles.append(role)
            await db.commit()
            await db.refresh(user)
        return user

    @staticmethod
    async def remove_role_from_user(db: AsyncSession, user_id: int, role_id: int) -> User:
        user = await user_crud.get_with_roles(db, user_id=user_id)
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        role = await role_crud.get(db, id=role_id)
        if not role:
            raise NotFoundException(f"Role with id {role_id} not found")
        if role in user.roles:
            user.roles.remove(role)
            await db.commit()
            await db.refresh(user)
        return user

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: int) -> list[Role]:
        user = await user_crud.get_with_roles(db, user_id=user_id)
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        return list(user.roles)

    @staticmethod
    async def check_user_permission(db: AsyncSession, user_id: int, permission_code: str) -> bool:
        user = await user_crud.get_with_roles(db, user_id=user_id)
        if not user:
            return False
        for role in user.roles:
            permissions = await permission_crud.get_by_role(db, role_id=role.id)
            for perm in permissions:
                if perm.code == permission_code:
                    return True
        return False


role_service = RoleService()
