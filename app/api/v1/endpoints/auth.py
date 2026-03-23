from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_user_db as get_db
from app.schemas.common import DataResponse
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse
from app.services.user import user_service


router = APIRouter()


@router.post(
    "/register",
    response_model=DataResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await user_service.create_user(db, user_in)
    return DataResponse(data=user, message="User created successfully")


@router.post("/login", response_model=DataResponse[Token])
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    token = await user_service.login_user(
        db, username=credentials.username, password=credentials.password
    )
    return DataResponse(data=token, message="Login successful")
