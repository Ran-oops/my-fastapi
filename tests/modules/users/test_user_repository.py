import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.repository import user_repo
from app.modules.users.schemas import UserCreate
from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestUserRepositoryGet:
    async def test_get_by_email_found(self, session: AsyncSession, test_user):
        result = await user_repo.get_by_email(session, email=test_user.email)
        assert result is not None
        assert result.email == test_user.email

    async def test_get_by_email_not_found(self, session: AsyncSession):
        result = await user_repo.get_by_email(session, email="nonexistent@example.com")
        assert result is None

    async def test_get_by_username_found(self, session: AsyncSession, test_user):
        result = await user_repo.get_by_username(session, username=test_user.username)
        assert result is not None
        assert result.username == test_user.username

    async def test_get_by_username_not_found(self, session: AsyncSession):
        result = await user_repo.get_by_username(session, username="nonexistent")
        assert result is None

    async def test_get_found(self, session: AsyncSession, test_user):
        result = await user_repo.get(session, id=test_user.id)
        assert result is not None
        assert result.id == test_user.id

    async def test_get_not_found(self, session: AsyncSession):
        result = await user_repo.get(session, id=NONEXISTENT_ID)
        assert result is None


@pytest.mark.asyncio
class TestUserRepositoryCreate:
    async def test_create_user_password_hashed(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        user_in = UserCreate(
            email=f"repo_{unique_id}@example.com",
            username=f"repouser_{unique_id}",
            password="plainpassword123",
            full_name="Repo Test",
            is_active=True,
        )
        user = await user_repo.create(session, user_in)
        assert user.id is not None
        assert user.hashed_password != "plainpassword123"
        assert len(user.hashed_password) > 0

    async def test_create_user_default_active(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        user_in = UserCreate(
            email=f"active_{unique_id}@example.com",
            username=f"activeuser_{unique_id}",
            password="password123",
            full_name="Active Test",
        )
        user = await user_repo.create(session, user_in)
        assert user.is_active is True


@pytest.mark.asyncio
class TestUserRepositoryAuthenticate:
    async def test_authenticate_success(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        username = f"authuser_{unique_id}"
        user_in = UserCreate(
            email=f"auth_{unique_id}@example.com",
            username=username,
            password="correctpassword123",
        )
        await user_repo.create(session, user_in)

        result = await user_repo.authenticate(session, username=username, password="correctpassword123")
        assert result is not None
        assert result.username == username

    async def test_authenticate_wrong_password(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        username = f"wrongpass_{unique_id}"
        user_in = UserCreate(
            email=f"wrong_{unique_id}@example.com",
            username=username,
            password="correctpassword123",
        )
        await user_repo.create(session, user_in)

        result = await user_repo.authenticate(session, username=username, password="wrongpassword123")
        assert result is None

    async def test_authenticate_nonexistent_user(self, session: AsyncSession):
        result = await user_repo.authenticate(session, username="nonexistent", password="password")
        assert result is None


@pytest.mark.asyncio
class TestUserRepositoryMulti:
    async def test_get_multi(self, session: AsyncSession, test_user):
        users = await user_repo.get_multi(session, skip=0, limit=10)
        assert len(users) >= 1
        assert any(u.id == test_user.id for u in users)

    async def test_count(self, session: AsyncSession, test_user):
        count = await user_repo.count(session)
        assert count >= 1
