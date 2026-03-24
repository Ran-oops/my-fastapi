from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.api.deps import get_user_db as get_db
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.common import DataResponse, PaginatedResponse, PaginationParams
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate, RoleWithPermissions, UserRoleAssign
from app.services.role import role_service


router = APIRouter()


@router.post("/", response_model=DataResponse[RoleResponse], status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    role = await role_service.create_role(db, role_in)
    return DataResponse(data=role, message="Role created successfully")


@router.get("/", response_model=PaginatedResponse[RoleWithPermissions])
async def get_roles(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    roles = await role_service.get_roles(db, skip=pagination.skip, limit=pagination.limit)
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


@router.get("/{role_id}", response_model=DataResponse[RoleWithPermissions])
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    role = await role_service.get_role_by_id(db, role_id)
    if not role:
        raise NotFoundException(f"Role {role_id} not found")
    return DataResponse(data=role)


@router.put("/{role_id}", response_model=DataResponse[RoleResponse])
async def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    role = await role_service.update_role(db, role_id, role_in)
    return DataResponse(data=role, message="Role updated successfully")


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    await role_service.delete_role(db, role_id)
    return None


@router.post("/assign", response_model=DataResponse[dict])
async def assign_role_to_user(
    assignment: UserRoleAssign,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    user = await role_service.assign_role_to_user(db, assignment.user_id, assignment.role_id)
    return DataResponse(
        data={"user_id": user.id, "role_id": assignment.role_id},
        message="Role assigned successfully",
    )


@router.delete("/assign/{user_id}/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    await role_service.remove_role_from_user(db, user_id, role_id)
    return None


@router.get("/users/{user_id}", response_model=DataResponse[list[RoleResponse]])
async def get_user_roles(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    roles = await role_service.get_user_roles(db, user_id)
    return DataResponse(data=roles)
