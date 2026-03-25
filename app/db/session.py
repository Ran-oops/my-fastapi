from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

user_engine: AsyncEngine = create_async_engine(
    settings.USER_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

business_engine: AsyncEngine = create_async_engine(
    settings.BUSINESS_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

config_engine: AsyncEngine = create_async_engine(
    settings.CONFIG_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

UserSessionFactory = async_sessionmaker(
    user_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

BusinessSessionFactory = async_sessionmaker(
    business_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

ConfigSessionFactory = async_sessionmaker(
    config_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_user_session():
    async with UserSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_business_session():
    async with BusinessSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_config_session():
    async with ConfigSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()
