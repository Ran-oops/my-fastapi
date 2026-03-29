from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import verify_token
from app.db.session import get_session
from app.modules.users.models import User
from app.modules.users.repository import user_repo


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(session: AsyncSession = Depends(get_session), token: str = Depends(oauth2_scheme)) -> User:
    user_id = verify_token(token)
    if user_id is None:
        raise UnauthorizedException("Could not validate credentials")
    user = await user_repo.get(session, id=int(user_id))
    if user is None:
        raise UnauthorizedException("User not found")
    if not user.is_active:
        raise UnauthorizedException("Inactive user")
    return user


async def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise ForbiddenException("The user doesn't have enough privileges")
    return current_user
