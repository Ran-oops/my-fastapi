from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, declared_attr

from app.core.config import settings


# =============================================================================
# SQLAlchemy Base Classes
# =============================================================================


class UserBase:
    """Base class for User Database models (PostgreSQL)"""

    @declared_attr
    def created_at(cls):
        return Column(DateTime, server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class BusinessBase:
    """Base class for Business Database models (SQL Server)"""

    @declared_attr
    def created_at(cls):
        return Column(DateTime, server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ConfigBase:
    """Base class for Config Database models (MySQL - Read Only)"""

    pass


UserDBBase = declarative_base(cls=UserBase)
BusinessDBBase = declarative_base(cls=BusinessBase)
ConfigDBBase = declarative_base(cls=ConfigBase)


# =============================================================================
# CRUD Base Class
# =============================================================================


class CRUDBase[ModelType, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel]:
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        result = await db.execute(select(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        return result.scalar_one_or_none()

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        result = await db.execute(
            select(self.model)
            .order_by(self.model.id.desc())  # type: ignore[attr-defined]
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self, db: AsyncSession) -> int:
        result = await db.execute(select(func.count()).select_from(self.model))
        scalar_result = result.scalar()
        return scalar_result if scalar_result is not None else 0

    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, id: int) -> ModelType | None:
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj


# =============================================================================
# Database Engines & Sessions
# =============================================================================


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


# =============================================================================
# Dependency Injection
# =============================================================================


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
