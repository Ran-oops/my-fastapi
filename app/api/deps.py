"""FastAPI dependency injection utilities.

This module provides FastAPI dependencies that integrate with the
dependency-injector container. It bridges the gap between FastAPI's
dependency injection system and the application's DI container.

Example:
    from fastapi import Depends
    from app.api.deps import get_db, get_current_user

    @router.get("/users")
    async def list_users(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        pass
"""

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.container import container
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import verify_token
from app.db.session import get_session
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_db() -> AsyncSession:
    """Get database session from the DI container.

    This is an async generator that yields a database session
    from the container's db_session provider.

    Yields:
        AsyncSession: Database session
    """
    async for session in container.db_session():
        yield session


# For backwards compatibility, keep get_session as the primary dependency
get_db_session = get_session


async def get_user_repository() -> UserRepository:
    """Get UserRepository from the DI container.

    Returns:
        UserRepository instance from the container
    """
    return container.user_repository()


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    token: str = Depends(oauth2_scheme),
) -> User:
    """Get the current authenticated user.

    This dependency:
    1. Validates the JWT token
    2. Retrieves the user from the repository (via DI container)
    3. Checks if the user is active

    Args:
        session: Database session (injected)
        token: JWT token from OAuth2 scheme (injected)

    Returns:
        User: The authenticated user

    Raises:
        UnauthorizedException: If token is invalid, user not found, or inactive
    """
    user_id = verify_token(token)
    if user_id is None:
        raise UnauthorizedException("Could not validate credentials")

    # Get repository from container
    user_repo = container.user_repository()
    user = await user_repo.get(session, id=int(user_id))

    if user is None:
        raise UnauthorizedException("User not found")
    if not user.is_active:
        raise UnauthorizedException("Inactive user")

    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current user and verify they are a superuser.

    Args:
        current_user: The current authenticated user (injected)

    Returns:
        User: The authenticated superuser

    Raises:
        ForbiddenException: If the user is not a superuser
    """
    if not current_user.is_superuser:
        raise ForbiddenException("The user doesn't have enough privileges")
    return current_user


async def get_optional_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Get the current user if authenticated, otherwise None.

    This is useful for endpoints that can work with or without authentication.

    Args:
        request: FastAPI request object
        session: Database session (injected)

    Returns:
        User | None: The authenticated user or None
    """
    # Try to get token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "")
    user_id = verify_token(token)

    if user_id is None:
        return None

    # Get repository from container
    user_repo = container.user_repository()
    user = await user_repo.get(session, id=int(user_id))

    if user is None or not user.is_active:
        return None

    return user
