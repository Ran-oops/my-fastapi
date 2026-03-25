from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_user_session
from app.common.pagination import PaginatedResponse, PaginationParams
from app.common.schemas import DataResponse
from app.core.exceptions import NotFoundException
from app.modules.roles import service as role_service
from app.modules.roles.schemas import (
    PermissionCreate,
    PermissionRead,
    PermissionUpdate,
    RoleCreate,
    RoleRead,
    RoleUpdate,
    RoleWithPermissions,
    UserRoleAssign,
)
from app.modules.users.models import User


router = APIRouter()


@router.post("/roles/", response_model=DataResponse[RoleRead], status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    role = await role_service.create_role(session, data)
    return DataResponse(data=role, message="Role created successfully")


@router.get("/roles/", response_model=PaginatedResponse[RoleWithPermissions])
async def get_roles(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    roles = await role_service.get_roles(session, skip=pagination.skip, limit=pagination.limit)
    total = len(roles)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=roles,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Roles retrieved successfully",
    )


@router.get("/roles/{role_id}", response_model=DataResponse[RoleWithPermissions])
async def get_role(
    role_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    role = await role_service.get_role_by_id(session, role_id)
    if not role:
        raise NotFoundException(f"Role {role_id} not found")
    return DataResponse(data=role)


@router.put("/roles/{role_id}", response_model=DataResponse[RoleRead])
async def update_role(
    role_id: int,
    data: RoleUpdate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    role = await role_service.update_role(session, role_id, data)
    return DataResponse(data=role, message="Role updated successfully")


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await role_service.delete_role(session, role_id)
    return None


@router.post("/roles/assign", response_model=DataResponse[dict])
async def assign_role_to_user(
    assignment: UserRoleAssign,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    user = await role_service.assign_role_to_user(session, assignment.user_id, assignment.role_id)
    return DataResponse(
        data={"user_id": user.id, "role_id": assignment.role_id},
        message="Role assigned successfully",
    )


@router.delete("/roles/assign/{user_id}/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await role_service.remove_role_from_user(session, user_id, role_id)
    return None


@router.get("/roles/users/{user_id}", response_model=DataResponse[list[RoleRead]])
async def get_user_roles(
    user_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    roles = await role_service.get_user_roles(session, user_id)
    return DataResponse(data=roles)


@router.post("/permissions/", response_model=DataResponse[PermissionRead], status_code=status.HTTP_201_CREATED)
async def create_permission(
    data: PermissionCreate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    permission = await role_service.create_permission(session, data)
    return DataResponse(data=permission, message="Permission created successfully")


@router.get("/permissions/", response_model=PaginatedResponse[PermissionRead])
async def get_permissions(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    permissions = await role_service.get_permissions(session, skip=pagination.skip, limit=pagination.limit)
    total = len(permissions)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=permissions,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Permissions retrieved successfully",
    )


@router.get("/permissions/{permission_id}", response_model=DataResponse[PermissionRead])
async def get_permission(
    permission_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    permission = await role_service.get_permission_by_id(session, permission_id)
    if not permission:
        raise NotFoundException(f"Permission {permission_id} not found")
    return DataResponse(data=permission)


@router.put("/permissions/{permission_id}", response_model=DataResponse[PermissionRead])
async def update_permission(
    permission_id: int,
    data: PermissionUpdate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    permission = await role_service.update_permission(session, permission_id, data)
    return DataResponse(data=permission, message="Permission updated successfully")


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await role_service.delete_permission(session, permission_id)
    return None


@router.get("/permissions/roles/{role_id}", response_model=DataResponse[list[PermissionRead]])
async def get_role_permissions(
    role_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    permissions = await role_service.get_role_permissions(session, role_id)
    return DataResponse(data=permissions)
