from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.core.security import create_access_token
from app.modules.users.models import User
from app.modules.users.repository import user_repository
from app.modules.users.schemas import Token, UserCreate, UserUpdate


class UserService:
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
        return await user_repository.get(db, id=user_id)

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        return await user_repository.get_by_email(db, email=email)

    @staticmethod
    async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
        users = await user_repository.get_multi(db, skip=skip, limit=limit)
        return list(users)

    @staticmethod
    async def get_users_count(db: AsyncSession) -> int:
        return await user_repository.count(db)

    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
        existing = await user_repository.get_by_email(db, email=user_in.email)
        if existing:
            raise ConflictException(f"Email {user_in.email} already registered")
        existing = await user_repository.get_by_username(db, username=user_in.username)
        if existing:
            raise ConflictException(f"Username {user_in.username} already taken")
        return await user_repository.create(db, obj_in=user_in)

    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, user_in: UserUpdate) -> User:
        user = await user_repository.get(db, id=user_id)
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        if user_in.email and user_in.email != user.email:
            existing = await user_repository.get_by_email(db, email=user_in.email)
            if existing:
                raise ConflictException(f"Email {user_in.email} already registered")
        if user_in.username and user_in.username != user.username:
            existing = await user_repository.get_by_username(db, username=user_in.username)
            if existing:
                raise ConflictException(f"Username {user_in.username} already taken")
        return await user_repository.update(db, db_obj=user, obj_in=user_in)

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int) -> User:
        user = await user_repository.get(db, id=user_id)
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        return await user_repository.delete(db, id=user_id)

    @staticmethod
    async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
        return await user_repository.authenticate(db, username=username, password=password)

    @staticmethod
    async def login_user(db: AsyncSession, username: str, password: str) -> Token:
        user = await UserService.authenticate_user(db, username, password)
        if not user:
            raise UnauthorizedException("Invalid credentials")
        if user.is_active is False:
            raise UnauthorizedException("Inactive user")
        access_token = create_access_token(subject=str(user.id))
        return Token(access_token=access_token)


user_service = UserService()
