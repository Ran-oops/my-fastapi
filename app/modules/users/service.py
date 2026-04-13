from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache, invalidate_cache
from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.core.security import create_access_token, create_refresh_token, verify_refresh_token
from app.modules.search.utils import update_user_search_vector
from app.modules.users.models import User
from app.modules.users.repository import user_repo
from app.modules.users.schemas import Token, UserCreate, UserUpdate


@cache(ttl=300, key_builder=lambda session, user_id: f"users:id:{user_id}")
async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    """Get user by ID with caching.

    Cache key: users:id:{user_id}
    TTL: 5 minutes
    """
    return await user_repo.get(session, id=user_id)


@cache(ttl=300, key_builder=lambda session, email: f"users:email:{email}")
async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Get user by email with caching.

    Cache key: users:email:{email}
    TTL: 5 minutes
    """
    return await user_repo.get_by_email(session, email=email)


@cache(ttl=60, key_builder=lambda session, skip=0, limit=100: f"users:list:skip:{skip}:limit:{limit}")
async def get_users(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    """Get users list with caching (short TTL due to frequent changes).

    Cache key: users:list:skip:{skip}:limit:{limit}
    TTL: 1 minute
    """
    users = await user_repo.get_multi(session, skip=skip, limit=limit)
    return list(users)


@cache(ttl=60, prefix="users")
async def get_users_count(session: AsyncSession) -> int:
    """Get total users count with caching (short TTL).

    Cache key: users:{module}.{function}
    TTL: 1 minute
    """
    return await user_repo.count(session)


@invalidate_cache(pattern="users:*")
async def create_user(session: AsyncSession, data: UserCreate) -> User:
    """Create a new user and invalidate all users cache.

    Invalidates: All cache keys matching 'users:*'
    """
    existing = await user_repo.get_by_email(session, email=data.email)
    if existing:
        raise ConflictException(f"Email {data.email} already registered")
    existing = await user_repo.get_by_username(session, username=data.username)
    if existing:
        raise ConflictException(f"Username {data.username} already taken")
    user = await user_repo.create(session, data=data)
    update_user_search_vector(user)
    return user


@invalidate_cache(pattern="users:*")
async def update_user(session: AsyncSession, user_id: int, data: UserUpdate) -> User:
    """Update user and invalidate users cache.

    Invalidates: All cache keys matching 'users:*' (including specific user caches)
    """
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


@invalidate_cache(pattern="users:*")
async def delete_user(session: AsyncSession, user_id: int) -> User:
    """Delete user and invalidate users cache.

    Invalidates: All cache keys matching 'users:*'
    """
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
    refresh_token = create_refresh_token(subject=str(user.id))
    return Token(access_token=access_token, refresh_token=refresh_token)


async def refresh_access_token(refresh_token: str) -> Token:
    user_id = verify_refresh_token(refresh_token)
    if not user_id:
        raise UnauthorizedException("Invalid refresh token")
    new_access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)
    return Token(access_token=new_access_token, refresh_token=new_refresh_token)
