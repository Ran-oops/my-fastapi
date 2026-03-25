from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.db.repository import BaseRepository
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, session: AsyncSession, username: str) -> User | None:
        result = await session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_with_roles(self, session: AsyncSession, user_id: int) -> User | None:
        result = await session.execute(select(User).where(User.id == user_id).options(selectinload(User.roles)))
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, data: UserCreate) -> User:
        instance = User(
            email=data.email,
            username=data.username,
            full_name=data.full_name,
            hashed_password=get_password_hash(data.password),
            is_active=data.is_active,
        )
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance

    async def authenticate(self, session: AsyncSession, username: str, password: str) -> User | None:
        user = await self.get_by_username(session, username=username)
        if not user:
            return None
        if not verify_password(password, str(user.hashed_password)):
            return None
        return user


user_repo = UserRepository(User)
