"""Users Router - Demonstrates Dependency Injection with dependency-injector.

This router demonstrates the new DI pattern:
- Services are obtained from the DI container
- Repositories are injected through the container
- Supports both direct service calls and container-based injection

Example with wiring:
    from dependency_injector.wiring import Provide, inject
    from app.core.container import Container

    @router.get("/")
    @inject
    async def list_users(
        user_service = Provide[Container.user_service],
    ):
        pass
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_session
from app.common.pagination import PaginatedResponse, PaginationParams
from app.common.schemas import DataResponse
from app.core.container import container
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.users import service as user_service
from app.modules.users.models import User
from app.modules.users.schemas import UserRead, UserUpdate


router = APIRouter()


@router.get("/me", response_model=DataResponse[UserRead])
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user.

    Args:
        current_user: The current authenticated user (injected)

    Returns:
        DataResponse with current user data
    """
    return DataResponse(data=current_user)


@router.get("/{user_id}", response_model=DataResponse[UserRead])
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    """Get user by ID.

    Args:
        user_id: The ID of the user to retrieve
        session: Database session (injected)
        _current_user: Current authenticated user (injected)

    Returns:
        DataResponse with user data

    Raises:
        NotFoundException: If user not found
    """
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise NotFoundException(f"User {user_id} not found")
    return DataResponse(data=user)


@router.get("/", response_model=PaginatedResponse[UserRead])
async def get_users(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    """Get paginated list of users.

    Requires superuser privileges.

    Args:
        pagination: Pagination parameters (injected)
        session: Database session (injected)
        _current_user: Current authenticated superuser (injected)

    Returns:
        PaginatedResponse with list of users
    """
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
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update user.

    Args:
        user_id: The ID of the user to update
        data: User update data
        session: Database session (injected)
        current_user: Current authenticated user (injected)

    Returns:
        DataResponse with updated user data

    Raises:
        ForbiddenException: If user doesn't have permission
    """
    if not current_user.is_superuser and current_user.id != user_id:
        raise ForbiddenException("Not enough permissions")
    user = await user_service.update_user(session, user_id, data)
    return DataResponse(data=user, message="User updated successfully")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    """Delete user.

    Requires superuser privileges.

    Args:
        user_id: The ID of the user to delete
        session: Database session (injected)
        _current_user: Current authenticated superuser (injected)

    Returns:
        None (204 No Content)
    """
    await user_service.delete_user(session, user_id)
    return None


# ==========================================================================
# DI Container Integration Examples
# ==========================================================================

# Example 1: Direct container access (current approach)
# Services are called directly, but repos are injected via deps.py


# Example 2: Repository injection from container
async def get_user_repository():
    """Get user repository from DI container.

    Returns:
        UserRepository instance
    """
    return container.user_repository()


# Example 3: Future pattern with @inject decorator
# from dependency_injector.wiring import Provide, inject
#
# @router.get("/container-test")
# @inject
# async def test_di(
#     user_repo: UserRepository = Depends(Provide[container.user_repository]),
# ):
#     """Test DI container injection."""
#     return {"message": f"Repository type: {type(user_repo).__name__}"}
