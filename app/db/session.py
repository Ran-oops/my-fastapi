from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


# User Database (PostgreSQL) - Read/Write
user_engine: AsyncEngine = create_async_engine(
    settings.USER_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

UserSessionLocal = async_sessionmaker(
    user_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Business Database (SQL Server) - Read/Write
business_engine: AsyncEngine = create_async_engine(
    settings.BUSINESS_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

BusinessSessionLocal = async_sessionmaker(
    business_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Config Database (MySQL) - Read Only
config_engine: AsyncEngine = create_async_engine(
    settings.CONFIG_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

ConfigSessionLocal = async_sessionmaker(
    config_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_user_db():
    async with UserSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_business_db():
    async with BusinessSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_config_db():
    async with ConfigSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
