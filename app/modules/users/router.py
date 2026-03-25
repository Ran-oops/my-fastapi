from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_user_session
from app.core.exceptions import NotFoundException
from app.common.schemas import DataResponse
from app.common.pagination import PaginatedResponse, PaginationParams
from app.modules.users.models import User
from app.modules.users.schemas import UserRead, UserUpdate, UserCreate, Token, UserLogin
from app.modules.users import service as user_service

router = APIRouter()


@router.post("/auth/register", response_model=DataResponse[UserRead], status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, session: AsyncSession = Depends(get_user_session)):
    user = await user_service.create_user(session, data)
    return DataResponse(data=user, message="User created successfully")


@router.post("/auth/login", response_model=DataResponse[Token])
async def login(credentials: UserLogin, session: AsyncSession = Depends(get_user_session)):
    token = await user_service.login_user(session, username=credentials.username, password=credentials.password)
    return DataResponse(data=token, message="Login successful")


@router.get("/me", response_model=DataResponse[UserRead])
async def get_me(current_user: User = Depends(get_current_user)):
    return DataResponse(data=current_user)


@router.get("/{user_id}", response_model=DataResponse[UserRead])
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise NotFoundException(f"User {user_id} not found")
    return DataResponse(data=user)


@router.get("/", response_model=PaginatedResponse[UserRead])
async def get_users(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    users = await user_service.get_users(session, skip=pagination.skip, limit=pagination.limit)
    total = await user_service.get_users_count(session)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=list(users),
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Users retrieved successfully",
    )


@router.put("/{user_id}", response_model=DataResponse[UserRead])
async def update_user(
    user_id: int,
    data: UserUpdate,
    session: AsyncSession = Depends(get_user_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    user = await user_service.update_user(session, user_id, data)
    return DataResponse(data=user, message="User updated successfully")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await user_service.delete_user(session, user_id)
    return None
