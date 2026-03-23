from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_active_superuser,
    get_current_user,
)
from app.api.deps import (
    get_user_db as get_db,
)
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.common import DataResponse, PaginatedResponse, PaginationParams
from app.schemas.user import UserResponse, UserUpdate
from app.services.user import user_service


router = APIRouter()


@router.get("/me", response_model=DataResponse[UserResponse])
async def get_me(current_user: User = Depends(get_current_user)):
    return DataResponse(data=current_user)


@router.get("/{user_id}", response_model=DataResponse[UserResponse])
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException(f"User {user_id} not found")
    return DataResponse(data=user)


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def get_users(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    users = await user_service.get_users(db, skip=pagination.skip, limit=pagination.limit)
    total = await user_service.get_users_count(db)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=list(users),
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Users retrieved successfully",
    )


@router.put("/{user_id}", response_model=DataResponse[UserResponse])
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.is_superuser is False and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    user = await user_service.update_user(db, user_id, user_in)
    return DataResponse(data=user, message="User updated successfully")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    await user_service.delete_user(db, user_id)
    return None
