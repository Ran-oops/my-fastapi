import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.modules.users import service as user_service
from app.modules.users.schemas import UserCreate, UserUpdate


@pytest.mark.asyncio
class TestUserServiceGet:
    async def test_get_user_by_id_found(self, session: AsyncSession, test_user):
        result = await user_service.get_user_by_id(session, test_user.id)
        assert result is not None
        assert result.id == test_user.id

    async def test_get_user_by_id_not_found(self, session: AsyncSession):
        result = await user_service.get_user_by_id(session, 99999)
        assert result is None

    async def test_get_user_by_email_found(self, session: AsyncSession, test_user):
        result = await user_service.get_user_by_email(session, test_user.email)
        assert result is not None
        assert result.email == test_user.email

    async def test_get_user_by_email_not_found(self, session: AsyncSession):
        result = await user_service.get_user_by_email(session, "nonexistent@example.com")
        assert result is None

    async def test_get_users_pagination(self, session: AsyncSession):
        for i in range(5):
            unique_id = uuid.uuid4().hex[:8]
            await user_service.create_user(
                session,
                UserCreate(
                    email=f"list{i}_{unique_id}@example.com",
                    username=f"listuser{i}_{unique_id}",
                    password="password123",
                    full_name=f"List User {i}",
                ),
            )
        users = await user_service.get_users(session, skip=0, limit=3)
        assert len(users) <= 3

    async def test_get_users_count(self, session: AsyncSession, test_user):
        count = await user_service.get_users_count(session)
        assert count >= 1


@pytest.mark.asyncio
class TestUserServiceCreate:
    async def test_create_user_success(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        user_in = UserCreate(
            email=f"new_{unique_id}@example.com",
            username=f"newuser_{unique_id}",
            password="password123",
            full_name="New User",
        )
        user = await user_service.create_user(session, user_in)
        assert user.id is not None
        assert user.email == f"new_{unique_id}@example.com"
        assert user.username == f"newuser_{unique_id}"
        assert user.hashed_password != "password123"

    async def test_create_user_duplicate_email(self, session: AsyncSession, test_user):
        unique_id = uuid.uuid4().hex[:8]
        with pytest.raises(ConflictException) as exc_info:
            await user_service.create_user(
                session,
                UserCreate(
                    email=test_user.email,
                    username=f"unique_{unique_id}",
                    password="password123",
                ),
            )
        assert "already registered" in str(exc_info.value)

    async def test_create_user_duplicate_username(self, session: AsyncSession, test_user):
        unique_id = uuid.uuid4().hex[:8]
        with pytest.raises(ConflictException) as exc_info:
            await user_service.create_user(
                session,
                UserCreate(
                    email=f"unique_{unique_id}@example.com",
                    username=test_user.username,
                    password="password123",
                ),
            )
        assert "already taken" in str(exc_info.value)


@pytest.mark.asyncio
class TestUserServiceUpdate:
    async def test_update_user_success(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        user = await user_service.create_user(
            session,
            UserCreate(
                email=f"update_{unique_id}@example.com",
                username=f"updateuser_{unique_id}",
                password="password123",
                full_name="Original Name",
            ),
        )
        update_in = UserUpdate(full_name="Updated Name")
        updated = await user_service.update_user(session, user.id, update_in)
        assert updated.full_name == "Updated Name"

    async def test_update_user_email(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        user = await user_service.create_user(
            session,
            UserCreate(
                email=f"oldemail_{unique_id}@example.com",
                username=f"emailuser_{unique_id}",
                password="password123",
            ),
        )
        new_unique = uuid.uuid4().hex[:8]
        update_in = UserUpdate(email=f"newemail_{new_unique}@example.com")
        updated = await user_service.update_user(session, user.id, update_in)
        assert updated.email == f"newemail_{new_unique}@example.com"

    async def test_update_user_not_found(self, session: AsyncSession):
        update_in = UserUpdate(full_name="New Name")
        with pytest.raises(NotFoundException) as exc_info:
            await user_service.update_user(session, 99999, update_in)
        assert "not found" in str(exc_info.value)

    async def test_update_user_duplicate_email(self, session: AsyncSession, test_user):
        unique_id = uuid.uuid4().hex[:8]
        user = await user_service.create_user(
            session,
            UserCreate(
                email=f"dupupdate_{unique_id}@example.com",
                username=f"dupuser_{unique_id}",
                password="password123",
            ),
        )
        with pytest.raises(ConflictException):
            await user_service.update_user(session, user.id, UserUpdate(email=test_user.email))


@pytest.mark.asyncio
class TestUserServiceDelete:
    async def test_delete_user_success(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        user = await user_service.create_user(
            session,
            UserCreate(
                email=f"delete_{unique_id}@example.com",
                username=f"deleteuser_{unique_id}",
                password="password123",
            ),
        )
        deleted = await user_service.delete_user(session, user.id)
        assert deleted.id == user.id
        result = await user_service.get_user_by_id(session, user.id)
        assert result is None

    async def test_delete_user_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundException) as exc_info:
            await user_service.delete_user(session, 99999)
        assert "not found" in str(exc_info.value)


@pytest.mark.asyncio
class TestUserServiceAuthenticate:
    async def test_authenticate_user_success(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        username = f"authuser_{unique_id}"
        await user_service.create_user(
            session,
            UserCreate(
                email=f"auth_{unique_id}@example.com",
                username=username,
                password="password123",
            ),
        )
        user = await user_service.authenticate_user(session, username, "password123")
        assert user is not None
        assert user.username == username

    async def test_authenticate_user_wrong_password(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        username = f"wrongpass_{unique_id}"
        await user_service.create_user(
            session,
            UserCreate(
                email=f"wrong_{unique_id}@example.com",
                username=username,
                password="password123",
            ),
        )
        user = await user_service.authenticate_user(session, username, "wrongpassword")
        assert user is None

    async def test_authenticate_user_nonexistent(self, session: AsyncSession):
        user = await user_service.authenticate_user(session, "nonexistent", "password")
        assert user is None


@pytest.mark.asyncio
class TestUserServiceLogin:
    async def test_login_user_success(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        username = f"loginuser_{unique_id}"
        await user_service.create_user(
            session,
            UserCreate(
                email=f"login_{unique_id}@example.com",
                username=username,
                password="password123",
            ),
        )
        token = await user_service.login_user(session, username, "password123")
        assert token.access_token is not None
        assert token.token_type == "bearer"

    async def test_login_user_invalid_credentials(self, session: AsyncSession):
        with pytest.raises(UnauthorizedException) as exc_info:
            await user_service.login_user(session, "nonexistent", "password")
        assert "Invalid credentials" in str(exc_info.value)

    async def test_login_user_inactive_user(self, session: AsyncSession):
        unique_id = uuid.uuid4().hex[:8]
        username = f"inactive_{unique_id}"
        await user_service.create_user(
            session,
            UserCreate(
                email=f"inactive_{unique_id}@example.com",
                username=username,
                password="password123",
                is_active=False,
            ),
        )
        with pytest.raises(UnauthorizedException) as exc_info:
            await user_service.login_user(session, username, "password123")
        assert "Inactive user" in str(exc_info.value)
