from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.api.deps import get_user_db as get_db
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.common import DataResponse, PaginatedResponse, PaginationParams
from app.schemas.permission import PermissionCreate, PermissionResponse, PermissionUpdate
from app.services.permission import permission_service


router = APIRouter()


@router.post("/", response_model=DataResponse[PermissionResponse], status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission_in: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    permission = await permission_service.create_permission(db, permission_in)
    return DataResponse(data=permission, message="Permission created successfully")


@router.get("/", response_model=PaginatedResponse[PermissionResponse])
async def get_permissions(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    permissions = await permission_service.get_permissions(db, skip=pagination.skip, limit=pagination.limit)
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


@router.get("/{permission_id}", response_model=DataResponse[PermissionResponse])
async def get_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    permission = await permission_service.get_permission_by_id(db, permission_id)
    if not permission:
        raise NotFoundException(f"Permission {permission_id} not found")
    return DataResponse(data=permission)


@router.put("/{permission_id}", response_model=DataResponse[PermissionResponse])
async def update_permission(
    permission_id: int,
    permission_in: PermissionUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    permission = await permission_service.update_permission(db, permission_id, permission_in)
    return DataResponse(data=permission, message="Permission updated successfully")


@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    await permission_service.delete_permission(db, permission_id)
    return None


@router.get("/roles/{role_id}", response_model=DataResponse[list[PermissionResponse]])
async def get_role_permissions(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    permissions = await permission_service.get_role_permissions(db, role_id)
    return DataResponse(data=permissions)
