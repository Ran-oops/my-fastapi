from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.crud.permission import permission as permission_crud
from app.models.user import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate


class PermissionService:
    @staticmethod
    async def create_permission(db: AsyncSession, permission_in: PermissionCreate) -> Permission:
        existing = await permission_crud.get_by_code(db, code=permission_in.code)
        if existing:
            raise ConflictException(f"Permission with code '{permission_in.code}' already exists")
        return await permission_crud.create(db, obj_in=permission_in)

    @staticmethod
    async def update_permission(db: AsyncSession, permission_id: int, permission_in: PermissionUpdate) -> Permission:
        permission_obj = await permission_crud.get(db, id=permission_id)
        if not permission_obj:
            raise NotFoundException(f"Permission with id {permission_id} not found")
        return await permission_crud.update(db, db_obj=permission_obj, obj_in=permission_in)

    @staticmethod
    async def delete_permission(db: AsyncSession, permission_id: int) -> Permission:
        permission_obj = await permission_crud.get(db, id=permission_id)
        if not permission_obj:
            raise NotFoundException(f"Permission with id {permission_id} not found")
        roles = await permission_crud.get_roles(db, permission_id=permission_id)
        if roles:
            raise ConflictException(f"Cannot delete permission assigned to {len(roles)} roles")
        return await permission_crud.delete(db, id=permission_id)

    @staticmethod
    async def get_permission_by_id(db: AsyncSession, permission_id: int) -> Permission | None:
        return await permission_crud.get(db, id=permission_id)

    @staticmethod
    async def get_permissions(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Permission]:
        return await permission_crud.get_multi(db, skip=skip, limit=limit)

    @staticmethod
    async def get_role_permissions(db: AsyncSession, role_id: int) -> list[Permission]:
        return await permission_crud.get_by_role(db, role_id=role_id)


permission_service = PermissionService()
