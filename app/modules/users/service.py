from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.core.security import create_access_token
from app.modules.search.utils import update_user_search_vector
from app.modules.users.models import User
from app.modules.users.repository import user_repo
from app.modules.users.schemas import Token, UserCreate, UserUpdate


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await user_repo.get(session, id=user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await user_repo.get_by_email(session, email=email)


async def get_users(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    users = await user_repo.get_multi(session, skip=skip, limit=limit)
    return list(users)


async def get_users_count(session: AsyncSession) -> int:
    return await user_repo.count(session)


async def create_user(session: AsyncSession, data: UserCreate) -> User:
    existing = await user_repo.get_by_email(session, email=data.email)
    if existing:
        raise ConflictException(f"Email {data.email} already registered")
    existing = await user_repo.get_by_username(session, username=data.username)
    if existing:
        raise ConflictException(f"Username {data.username} already taken")
    user = await user_repo.create(session, data=data)
    update_user_search_vector(user)
    return user


async def update_user(session: AsyncSession, user_id: int, data: UserUpdate) -> User:
    user = await user_repo.get(session, id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    if data.email and data.email != user.email:
        existing = await user_repo.get_by_email(session, email=data.email)
        if existing:
            raise ConflictException(f"Email {data.email} already registered")
    if data.username and data.username != user.username:
        existing = await user_repo.get_by_username(session, username=data.username)
        if existing:
            raise ConflictException(f"Username {data.username} already taken")
    user = await user_repo.update(session, instance=user, data=data)
    update_user_search_vector(user)
    return user


async def delete_user(session: AsyncSession, user_id: int) -> User:
    user = await user_repo.get(session, id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    return await user_repo.delete(session, id=user_id)


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User | None:
    return await user_repo.authenticate(session, username=username, password=password)


async def login_user(session: AsyncSession, username: str, password: str) -> Token:
    user = await authenticate_user(session, username, password)
    if not user:
        raise UnauthorizedException("Invalid credentials")
    if not user.is_active:
        raise UnauthorizedException("Inactive user")
    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token)
