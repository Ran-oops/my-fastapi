import os
import uuid


# Set test SECRET_KEY before importing app modules to avoid warning
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32chars")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, get_password_hash
from app.db.base import BusinessBase, UserBase
from app.db.session import get_business_session, get_user_session
from app.main import app
from app.modules.users.models import User


# Shared test constants
TEST_PASSWORD = "testpassword123"
NONEXISTENT_ID = 99999


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, future=True)
TestingSessionFactory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session")
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.create_all)
        await conn.run_sync(BusinessBase.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(BusinessBase.metadata.drop_all)
        await conn.run_sync(UserBase.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(setup_test_db):
    async with TestingSessionFactory() as session:
        yield session
    await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(session):
    async def override_get_session():
        yield session

    async def override_get_business_session():
        yield session

    app.dependency_overrides[get_user_session] = override_get_session
    app.dependency_overrides[get_business_session] = override_get_business_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(session):
    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"testuser_{uid}@example.com",
        username=f"testuser_{uid}",
        hashed_password=get_password_hash(TEST_PASSWORD),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_superuser(session):
    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"superuser_{uid}@example.com",
        username=f"superuser_{uid}",
        hashed_password=get_password_hash(TEST_PASSWORD),
        full_name="Test Superuser",
        is_active=True,
        is_superuser=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def superuser_token(test_superuser):
    return create_access_token(subject=str(test_superuser.id))


@pytest_asyncio.fixture(scope="function")
async def user_token(test_user):
    return create_access_token(subject=str(test_user.id))


@pytest_asyncio.fixture(scope="function")
async def user_id(test_user):
    return test_user.id


@pytest_asyncio.fixture
async def superuser_headers(superuser_token):
    """Headers for admin API calls."""
    return {"Authorization": f"Bearer {superuser_token}"}


@pytest_asyncio.fixture
async def user_headers(user_token):
    """Headers for regular user API calls."""
    return {"Authorization": f"Bearer {user_token}"}
