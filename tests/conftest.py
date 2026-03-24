import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, get_password_hash
from app.db.base import UserDBBase as Base
from app.db.session import get_user_db as get_db
from app.main import app
from app.modules.users.models import User


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session")
async def setup_test_db():
    """在测试会话开始时创建表."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(setup_test_db):
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    """创建测试用户."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    user = User(
        email=f"testuser_{unique_id}@example.com",
        username=f"testuser_{unique_id}",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def superuser_token(test_user):
    """创建超级用户token."""
    test_user.is_superuser = True
    return create_access_token(subject=str(test_user.id))


@pytest_asyncio.fixture(scope="function")
async def user_token(test_user):
    """创建普通用户token."""
    return create_access_token(subject=str(test_user.id))


@pytest_asyncio.fixture(scope="function")
async def user_id(test_user):
    """返回测试用户ID."""
    return test_user.id
