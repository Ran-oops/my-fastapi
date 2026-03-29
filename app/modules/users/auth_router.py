from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.common.schemas import DataResponse
from app.modules.users import service as user_service
from app.modules.users.schemas import Token, UserCreate, UserLogin, UserRead


router = APIRouter()


@router.post("/register", response_model=DataResponse[UserRead], status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, session: AsyncSession = Depends(get_session)):
    user = await user_service.create_user(session, data)
    return DataResponse(data=user, message="User created successfully")


@router.post("/login", response_model=DataResponse[Token])
async def login(credentials: UserLogin, session: AsyncSession = Depends(get_session)):
    token = await user_service.login_user(session, username=credentials.username, password=credentials.password)
    return DataResponse(data=token, message="Login successful")
