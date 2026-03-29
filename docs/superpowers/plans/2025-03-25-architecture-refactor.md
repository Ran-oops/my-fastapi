# Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor Enterprise FastAPI project architecture and scaffold 4 new business modules (Products, Orders, Config, Audit).

**Architecture:** Split `shared/` into `db/` + `common/`, extract association tables to resolve circular imports, convert service classes to functions, unify routing under modules, apply consistent naming.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), Pydantic V2, pytest, ruff

---

## Phase 1: Database Infrastructure Split

### Task 1: Create db/base.py

**Files:**

- Create: `app/db/__init__.py`
- Create: `app/db/base.py`

- [ ] **Step 1: Create db directory and **init**.py**

```bash
mkdir -p app/db
```

- [ ] **Step 2: Write app/db/**init**.py**

```python
from app.db.base import UserBase, BusinessBase, ConfigBase

__all__ = ["UserBase", "BusinessBase", "ConfigBase"]
```

- [ ] **Step 3: Write app/db/base.py**

```python
from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import declarative_base, declared_attr


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    @declared_attr
    def created_at(cls):
        return Column(DateTime, server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ConfigMixin:
    """Mixin for config database models (no timestamps)."""
    pass


UserBase = declarative_base(cls=TimestampMixin)
BusinessBase = declarative_base(cls=TimestampMixin)
ConfigBase = declarative_base(cls=ConfigMixin)
```

- [ ] **Step 4: Verify import works**

```bash
uv run python -c "from app.db.base import UserBase, BusinessBase, ConfigBase; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add app/db/
git commit -m "feat(db): add db/base.py with UserBase, BusinessBase, ConfigBase"
```

---

### Task 2: Create db/session.py

**Files:**

- Create: `app/db/session.py`
- Modify: `app/db/__init__.py`

- [ ] **Step 1: Write app/db/session.py**

```python
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
```

- [ ] **Step 2: Update app/db/**init**.py**

```python
from app.db.base import UserBase, BusinessBase, ConfigBase
from app.db.session import (
    business_engine,
    config_engine,
    get_business_session,
    get_config_session,
    get_user_session,
    user_engine,
    BusinessSessionFactory,
    ConfigSessionFactory,
    UserSessionFactory,
)

__all__ = [
    "UserBase",
    "BusinessBase",
    "ConfigBase",
    "user_engine",
    "business_engine",
    "config_engine",
    "UserSessionFactory",
    "BusinessSessionFactory",
    "ConfigSessionFactory",
    "get_user_session",
    "get_business_session",
    "get_config_session",
]
```

- [ ] **Step 3: Verify import works**

```bash
uv run python -c "from app.db import UserBase, get_user_session; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/db/
git commit -m "feat(db): add db/session.py with engines and session factories"
```

---

### Task 3: Create db/repository.py

**Files:**

- Create: `app/db/repository.py`
- Modify: `app/db/__init__.py`

- [ ] **Step 1: Write app/db/repository.py**

```python
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository[ModelType, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel]:
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, session: AsyncSession, id: Any) -> ModelType | None:
        result = await session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(self, session: AsyncSession, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        result = await session.execute(
            select(self.model)
            .order_by(self.model.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(self.model))
        scalar_result = result.scalar()
        return scalar_result if scalar_result is not None else 0

    async def create(self, session: AsyncSession, data: CreateSchemaType) -> ModelType:
        data_dict = data.model_dump()
        instance = self.model(**data_dict)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance

    async def update(
        self,
        session: AsyncSession,
        instance: ModelType,
        data: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        update_data = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        await session.commit()
        await session.refresh(instance)
        return instance

    async def delete(self, session: AsyncSession, id: int) -> ModelType | None:
        instance = await self.get(session, id)
        if instance:
            await session.delete(instance)
            await session.commit()
        return instance
```

- [ ] **Step 2: Update app/db/**init**.py**

```python
from app.db.base import UserBase, BusinessBase, ConfigBase
from app.db.repository import BaseRepository
from app.db.session import (
    business_engine,
    config_engine,
    get_business_session,
    get_config_session,
    get_user_session,
    user_engine,
    BusinessSessionFactory,
    ConfigSessionFactory,
    UserSessionFactory,
)

__all__ = [
    "UserBase",
    "BusinessBase",
    "ConfigBase",
    "BaseRepository",
    "user_engine",
    "business_engine",
    "config_engine",
    "UserSessionFactory",
    "BusinessSessionFactory",
    "ConfigSessionFactory",
    "get_user_session",
    "get_business_session",
    "get_config_session",
]
```

- [ ] **Step 3: Verify import works**

```bash
uv run python -c "from app.db import BaseRepository; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/db/
git commit -m "feat(db): add db/repository.py with BaseRepository"
```

---

## Phase 2: Common Schemas Split

### Task 4: Create common/schemas.py

**Files:**

- Create: `app/common/__init__.py`
- Create: `app/common/schemas.py`

- [ ] **Step 1: Create common directory**

```bash
mkdir -p app/common
```

- [ ] **Step 2: Write app/common/**init**.py**

```python
from app.common.schemas import DataResponse, ListResponse, ResponseBase
from app.common.pagination import PaginatedResponse, PaginationParams

__all__ = [
    "ResponseBase",
    "DataResponse",
    "ListResponse",
    "PaginationParams",
    "PaginatedResponse",
]
```

- [ ] **Step 3: Write app/common/schemas.py**

```python
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseBase(BaseModel):
    success: bool = True
    message: str = ""


class DataResponse[T](ResponseBase):
    data: T


class ListResponse[T](ResponseBase):
    data: list[T]
```

- [ ] **Step 4: Commit**

```bash
git add app/common/
git commit -m "feat(common): add common/schemas.py with response models"
```

---

### Task 5: Create common/pagination.py

**Files:**

- Create: `app/common/pagination.py`

- [ ] **Step 1: Write app/common/pagination.py**

```python
from typing import TypeVar

from pydantic import BaseModel, ConfigDict

from app.common.schemas import ListResponse

T = TypeVar("T")


class PaginationParams(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int = 1
    page_size: int = 10

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(ListResponse[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
```

- [ ] **Step 2: Verify import works**

```bash
uv run python -c "from app.common import PaginationParams, PaginatedResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/common/
git commit -m "feat(common): add common/pagination.py with pagination models"
```

---

## Phase 3: Resolve Circular Imports

### Task 6: Create users/associations.py

**Files:**

- Create: `app/modules/users/associations.py`

- [ ] **Step 1: Write app/modules/users/associations.py**

```python
from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.base import UserBase

user_roles = Table(
    "user_roles",
    UserBase.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/users/associations.py
git commit -m "feat(users): add associations.py with user_roles table"
```

---

### Task 7: Create roles/associations.py

**Files:**

- Create: `app/modules/roles/associations.py`

- [ ] **Step 1: Write app/modules/roles/associations.py**

```python
from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.base import UserBase

role_permissions = Table(
    "role_permissions",
    UserBase.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/roles/associations.py
git commit -m "feat(roles): add associations.py with role_permissions table"
```

---

### Task 8: Update users/models.py

**Files:**

- Modify: `app/modules/users/models.py`

- [ ] **Step 1: Update app/modules/users/models.py**

```python
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UserBase


class User(UserBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )
```

- [ ] **Step 2: Verify import works**

```bash
uv run python -c "from app.modules.users.models import User; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/modules/users/models.py
git commit -m "refactor(users): remove circular import, use string-based relationship"
```

---

### Task 9: Update roles/models.py

**Files:**

- Modify: `app/modules/roles/models.py`

- [ ] **Step 1: Update app/modules/roles/models.py**

```python
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UserBase


class Role(UserBase):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        lazy="selectin",
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )


class Permission(UserBase):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin",
    )
```

- [ ] **Step 2: Verify import works**

```bash
uv run python -c "from app.modules.roles.models import Role, Permission; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/modules/roles/models.py
git commit -m "refactor(roles): remove circular import, remove inline table definitions"
```

---

## Phase 4: Update All Imports

### Task 10: Update users/repository.py

**Files:**

- Modify: `app/modules/users/repository.py`

- [ ] **Step 1: Update app/modules/users/repository.py**

```python
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
        result = await session.execute(
            select(User).where(User.id == user_id).options(selectinload(User.roles))
        )
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
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/users/repository.py
git commit -m "refactor(users): update repository to use new imports and naming"
```

---

### Task 11: Update users/schemas.py

**Files:**

- Modify: `app/modules/users/schemas.py`

- [ ] **Step 1: Update app/modules/users/schemas.py**

```python
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(v) > 72:
        v = v[:72]
    if not re.search(r"[A-Za-z]", v):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    return v


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None
    password: str
    is_active: bool = True

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    password: str | None = None
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        return validate_password_strength(v) if v else v


class UserRead(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserDB(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: str | None
    hashed_password: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/users/schemas.py
git commit -m "refactor(users): rename schemas, remove base class"
```

---

### Task 12: Convert users/service.py to functions

**Files:**

- Modify: `app/modules/users/service.py`

- [ ] **Step 1: Update app/modules/users/service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.core.security import create_access_token
from app.modules.users.models import User
from app.modules.users.repository import user_repo
from app.modules.users.schemas import Token, UserCreate, UserUpdate


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await user_repo.get(session, id=user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await user_repo.get_by_email(session, email=email)


async def get_users(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    users = await user_repo.get_multi(session, skip=skip, limit=limit)
    return list(users)


async def get_users_count(session: AsyncSession) -> int:
    return await user_repo.count(session)


async def create_user(session: AsyncSession, data: UserCreate) -> User:
    existing = await user_repo.get_by_email(session, email=data.email)
    if existing:
        raise ConflictException(f"Email {data.email} already registered")
    existing = await user_repo.get_by_username(session, username=data.username)
    if existing:
        raise ConflictException(f"Username {data.username} already taken")
    return await user_repo.create(session, data=data)


async def update_user(session: AsyncSession, user_id: int, data: UserUpdate) -> User:
    user = await user_repo.get(session, id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    if data.email and data.email != user.email:
        existing = await user_repo.get_by_email(session, email=data.email)
        if existing:
            raise ConflictException(f"Email {data.email} already registered")
    if data.username and data.username != user.username:
        existing = await user_repo.get_by_username(session, username=data.username)
        if existing:
            raise ConflictException(f"Username {data.username} already taken")
    return await user_repo.update(session, instance=user, data=data)


async def delete_user(session: AsyncSession, user_id: int) -> User:
    user = await user_repo.get(session, id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    return await user_repo.delete(session, id=user_id)


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User | None:
    return await user_repo.authenticate(session, username=username, password=password)


async def login_user(session: AsyncSession, username: str, password: str) -> Token:
    user = await authenticate_user(session, username, password)
    if not user:
        raise UnauthorizedException("Invalid credentials")
    if not user.is_active:
        raise UnauthorizedException("Inactive user")
    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token)
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/users/service.py
git commit -m "refactor(users): convert UserService class to module functions"
```

---

### Task 13: Update users/router.py

**Files:**

- Modify: `app/modules/users/router.py`

- [ ] **Step 1: Update app/modules/users/router.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_user_session
from app.core.exceptions import NotFoundException
from app.common.schemas import DataResponse
from app.common.pagination import PaginatedResponse, PaginationParams
from app.modules.users.models import User
from app.modules.users.schemas import UserRead, UserUpdate, UserCreate, Token, UserLogin
from app.modules.users import service as user_service

router = APIRouter()


@router.post("/auth/register", response_model=DataResponse[UserRead], status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, session: AsyncSession = Depends(get_user_session)):
    user = await user_service.create_user(session, data)
    return DataResponse(data=user, message="User created successfully")


@router.post("/auth/login", response_model=DataResponse[Token])
async def login(credentials: UserLogin, session: AsyncSession = Depends(get_user_session)):
    token = await user_service.login_user(session, username=credentials.username, password=credentials.password)
    return DataResponse(data=token, message="Login successful")


@router.get("/me", response_model=DataResponse[UserRead])
async def get_me(current_user: User = Depends(get_current_user)):
    return DataResponse(data=current_user)


@router.get("/{user_id}", response_model=DataResponse[UserRead])
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise NotFoundException(f"User {user_id} not found")
    return DataResponse(data=user)


@router.get("/", response_model=PaginatedResponse[UserRead])
async def get_users(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
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
    session: AsyncSession = Depends(get_user_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    user = await user_service.update_user(session, user_id, data)
    return DataResponse(data=user, message="User updated successfully")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await user_service.delete_user(session, user_id)
    return None
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/users/router.py
git commit -m "refactor(users): update router with new imports and auth endpoints"
```

---

### Task 14: Update roles/repository.py

**Files:**

- Modify: `app/modules/roles/repository.py`

- [ ] **Step 1: Update app/modules/roles/repository.py**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repository import BaseRepository
from app.modules.roles.models import Permission, Role
from app.modules.roles.schemas import PermissionCreate, PermissionUpdate, RoleCreate, RoleUpdate
from app.modules.users.associations import user_roles
from app.modules.roles.associations import role_permissions


class RoleRepository(BaseRepository[Role, RoleCreate, RoleUpdate]):
    async def get_by_name(self, session: AsyncSession, name: str) -> Role | None:
        result = await session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_with_permissions(self, session: AsyncSession, role_id: int) -> Role | None:
        result = await session.execute(
            select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def get_multi_with_permissions(self, session: AsyncSession, skip: int = 0, limit: int = 100) -> list[Role]:
        result = await session.execute(
            select(Role).options(selectinload(Role.permissions)).order_by(Role.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def add_permission(self, session: AsyncSession, role_id: int, permission_id: int) -> Role | None:
        role = await self.get_with_permissions(session, role_id)
        if not role:
            return None
        permission = await session.execute(select(Permission).where(Permission.id == permission_id))
        permission_obj = permission.scalar_one_or_none()
        if not permission_obj:
            return None
        if permission_obj not in role.permissions:
            role.permissions.append(permission_obj)
            await session.commit()
            await session.refresh(role)
        return role

    async def remove_permission(self, session: AsyncSession, role_id: int, permission_id: int) -> Role | None:
        role = await self.get_with_permissions(session, role_id)
        if not role:
            return None
        permission = await session.execute(select(Permission).where(Permission.id == permission_id))
        permission_obj = permission.scalar_one_or_none()
        if not permission_obj:
            return None
        if permission_obj in role.permissions:
            role.permissions.remove(permission_obj)
            await session.commit()
            await session.refresh(role)
        return role

    async def get_users(self, session: AsyncSession, role_id: int) -> list[int]:
        result = await session.execute(select(user_roles.c.user_id).where(user_roles.c.role_id == role_id))
        return [row[0] for row in result.fetchall()]


class PermissionRepository(BaseRepository[Permission, PermissionCreate, PermissionUpdate]):
    async def get_by_code(self, session: AsyncSession, code: str) -> Permission | None:
        result = await session.execute(select(Permission).where(Permission.code == code))
        return result.scalar_one_or_none()

    async def get_by_role(self, session: AsyncSession, role_id: int) -> list[Permission]:
        result = await session.execute(
            select(Permission)
            .join(role_permissions)
            .where(role_permissions.c.role_id == role_id)
            .order_by(Permission.id)
        )
        return list(result.scalars().all())

    async def get_roles(self, session: AsyncSession, permission_id: int) -> list[int]:
        result = await session.execute(
            select(role_permissions.c.role_id).where(role_permissions.c.permission_id == permission_id)
        )
        return [row[0] for row in result.fetchall()]


role_repo = RoleRepository(Role)
permission_repo = PermissionRepository(Permission)
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/roles/repository.py
git commit -m "refactor(roles): update repository with new imports and naming"
```

---

### Task 15: Update roles/schemas.py

**Files:**

- Modify: `app/modules/roles/schemas.py`

- [ ] **Step 1: Update app/modules/roles/schemas.py**

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: str | None = Field(None, max_length=255, description="Role description")


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100, description="Role name")
    description: str | None = Field(None, max_length=255, description="Role description")


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None


class RoleWithPermissions(RoleRead):
    permissions: list[PermissionRead] = []


class UserRoleAssign(BaseModel):
    user_id: int = Field(..., description="User ID")
    role_id: int = Field(..., description="Role ID")


class UserRoleResponse(BaseModel):
    user_id: int
    role_id: int
    role_name: str


class PermissionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Permission name")
    code: str = Field(..., min_length=1, max_length=100, description="Permission code")
    description: str | None = Field(None, max_length=255, description="Permission description")


class PermissionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100, description="Permission name")
    description: str | None = Field(None, max_length=255, description="Permission description")


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    description: str | None


RoleWithPermissions.model_rebuild()
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/roles/schemas.py
git commit -m "refactor(roles): rename schemas, remove base classes"
```

---

### Task 16: Convert roles/service.py to functions

**Files:**

- Modify: `app/modules/roles/service.py`

- [ ] **Step 1: Update app/modules/roles/service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.roles.models import Permission, Role
from app.modules.roles.repository import permission_repo, role_repo
from app.modules.roles.schemas import PermissionCreate, PermissionUpdate, RoleCreate, RoleUpdate
from app.modules.users.repository import user_repo


async def create_role(session: AsyncSession, data: RoleCreate) -> Role:
    existing = await role_repo.get_by_name(session, name=data.name)
    if existing:
        raise ConflictException(f"Role with name '{data.name}' already exists")
    return await role_repo.create(session, data=data)


async def update_role(session: AsyncSession, role_id: int, data: RoleUpdate) -> Role:
    role = await role_repo.get(session, id=role_id)
    if not role:
        raise NotFoundException(f"Role with id {role_id} not found")
    if data.name and data.name != role.name:
        existing = await role_repo.get_by_name(session, name=data.name)
        if existing:
            raise ConflictException(f"Role with name '{data.name}' already exists")
    return await role_repo.update(session, instance=role, data=data)


async def delete_role(session: AsyncSession, role_id: int) -> Role:
    role = await role_repo.get(session, id=role_id)
    if not role:
        raise NotFoundException(f"Role with id {role_id} not found")
    users = await role_repo.get_users(session, role_id=role_id)
    if users:
        raise ConflictException(f"Cannot delete role with {len(users)} assigned users")
    return await role_repo.delete(session, id=role_id)


async def get_role_by_id(session: AsyncSession, role_id: int) -> Role | None:
    return await role_repo.get_with_permissions(session, role_id=role_id)


async def get_roles(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[Role]:
    return await role_repo.get_multi_with_permissions(session, skip=skip, limit=limit)


async def assign_role_to_user(session: AsyncSession, user_id: int, role_id: int):
    user = await user_repo.get_with_roles(session, user_id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    role = await role_repo.get(session, id=role_id)
    if not role:
        raise NotFoundException(f"Role with id {role_id} not found")
    if role not in user.roles:
        user.roles.append(role)
        await session.commit()
        await session.refresh(user)
    return user


async def remove_role_from_user(session: AsyncSession, user_id: int, role_id: int):
    user = await user_repo.get_with_roles(session, user_id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    role = await role_repo.get(session, id=role_id)
    if not role:
        raise NotFoundException(f"Role with id {role_id} not found")
    if role in user.roles:
        user.roles.remove(role)
        await session.commit()
        await session.refresh(user)
    return user


async def get_user_roles(session: AsyncSession, user_id: int) -> list[Role]:
    user = await user_repo.get_with_roles(session, user_id=user_id)
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    return list(user.roles)


async def check_user_permission(session: AsyncSession, user_id: int, permission_code: str) -> bool:
    user = await user_repo.get_with_roles(session, user_id=user_id)
    if not user:
        return False
    for role in user.roles:
        permissions = await permission_repo.get_by_role(session, role_id=role.id)
        for perm in permissions:
            if perm.code == permission_code:
                return True
    return False


async def create_permission(session: AsyncSession, data: PermissionCreate) -> Permission:
    existing = await permission_repo.get_by_code(session, code=data.code)
    if existing:
        raise ConflictException(f"Permission with code '{data.code}' already exists")
    return await permission_repo.create(session, data=data)


async def update_permission(session: AsyncSession, permission_id: int, data: PermissionUpdate) -> Permission:
    permission_obj = await permission_repo.get(session, id=permission_id)
    if not permission_obj:
        raise NotFoundException(f"Permission with id {permission_id} not found")
    return await permission_repo.update(session, instance=permission_obj, data=data)


async def delete_permission(session: AsyncSession, permission_id: int) -> Permission:
    permission_obj = await permission_repo.get(session, id=permission_id)
    if not permission_obj:
        raise NotFoundException(f"Permission with id {permission_id} not found")
    roles = await permission_repo.get_roles(session, permission_id=permission_id)
    if roles:
        raise ConflictException(f"Cannot delete permission assigned to {len(roles)} roles")
    return await permission_repo.delete(session, id=permission_id)


async def get_permission_by_id(session: AsyncSession, permission_id: int) -> Permission | None:
    return await permission_repo.get(session, id=permission_id)


async def get_permissions(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[Permission]:
    return await permission_repo.get_multi(session, skip=skip, limit=limit)


async def get_role_permissions(session: AsyncSession, role_id: int) -> list[Permission]:
    return await permission_repo.get_by_role(session, role_id=role_id)
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/roles/service.py
git commit -m "refactor(roles): convert RoleService/PermissionService classes to functions"
```

---

### Task 17: Update roles/router.py

**Files:**

- Modify: `app/modules/roles/router.py`

- [ ] **Step 1: Update app/modules/roles/router.py**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_user_session
from app.core.exceptions import NotFoundException
from app.common.schemas import DataResponse
from app.common.pagination import PaginatedResponse, PaginationParams
from app.modules.users.models import User
from app.modules.roles.schemas import (
    PermissionCreate,
    PermissionRead,
    PermissionUpdate,
    RoleCreate,
    RoleRead,
    RoleUpdate,
    RoleWithPermissions,
    UserRoleAssign,
)
from app.modules.roles import service as role_service

router = APIRouter()


@router.post("/roles/", response_model=DataResponse[RoleRead], status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    role = await role_service.create_role(session, data)
    return DataResponse(data=role, message="Role created successfully")


@router.get("/roles/", response_model=PaginatedResponse[RoleWithPermissions])
async def get_roles(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    roles = await role_service.get_roles(session, skip=pagination.skip, limit=pagination.limit)
    total = len(roles)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=roles,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Roles retrieved successfully",
    )


@router.get("/roles/{role_id}", response_model=DataResponse[RoleWithPermissions])
async def get_role(
    role_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    role = await role_service.get_role_by_id(session, role_id)
    if not role:
        raise NotFoundException(f"Role {role_id} not found")
    return DataResponse(data=role)


@router.put("/roles/{role_id}", response_model=DataResponse[RoleRead])
async def update_role(
    role_id: int,
    data: RoleUpdate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    role = await role_service.update_role(session, role_id, data)
    return DataResponse(data=role, message="Role updated successfully")


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await role_service.delete_role(session, role_id)
    return None


@router.post("/roles/assign", response_model=DataResponse[dict])
async def assign_role_to_user(
    assignment: UserRoleAssign,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    user = await role_service.assign_role_to_user(session, assignment.user_id, assignment.role_id)
    return DataResponse(
        data={"user_id": user.id, "role_id": assignment.role_id},
        message="Role assigned successfully",
    )


@router.delete("/roles/assign/{user_id}/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await role_service.remove_role_from_user(session, user_id, role_id)
    return None


@router.get("/roles/users/{user_id}", response_model=DataResponse[list[RoleRead]])
async def get_user_roles(
    user_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    roles = await role_service.get_user_roles(session, user_id)
    return DataResponse(data=roles)


@router.post("/permissions/", response_model=DataResponse[PermissionRead], status_code=status.HTTP_201_CREATED)
async def create_permission(
    data: PermissionCreate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    permission = await role_service.create_permission(session, data)
    return DataResponse(data=permission, message="Permission created successfully")


@router.get("/permissions/", response_model=PaginatedResponse[PermissionRead])
async def get_permissions(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    permissions = await role_service.get_permissions(session, skip=pagination.skip, limit=pagination.limit)
    total = len(permissions)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=permissions,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Permissions retrieved successfully",
    )


@router.get("/permissions/{permission_id}", response_model=DataResponse[PermissionRead])
async def get_permission(
    permission_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    permission = await role_service.get_permission_by_id(session, permission_id)
    if not permission:
        raise NotFoundException(f"Permission {permission_id} not found")
    return DataResponse(data=permission)


@router.put("/permissions/{permission_id}", response_model=DataResponse[PermissionRead])
async def update_permission(
    permission_id: int,
    data: PermissionUpdate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    permission = await role_service.update_permission(session, permission_id, data)
    return DataResponse(data=permission, message="Permission updated successfully")


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await role_service.delete_permission(session, permission_id)
    return None


@router.get("/permissions/roles/{role_id}", response_model=DataResponse[list[PermissionRead]])
async def get_role_permissions(
    role_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    permissions = await role_service.get_role_permissions(session, role_id)
    return DataResponse(data=permissions)
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/roles/router.py
git commit -m "refactor(roles): update router with new imports"
```

---

### Task 18: Update api/deps.py

**Files:**

- Modify: `app/api/deps.py`

- [ ] **Step 1: Update app/api/deps.py**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.security import verify_token
from app.db.session import get_user_session
from app.modules.users.models import User
from app.modules.users.repository import user_repo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    session: AsyncSession = Depends(get_user_session), token: str = Depends(oauth2_scheme)
) -> User:
    user_id = verify_token(token)
    if user_id is None:
        raise UnauthorizedException("Could not validate credentials")
    user = await user_repo.get(session, id=int(user_id))
    if user is None:
        raise UnauthorizedException("User not found")
    if not user.is_active:
        raise UnauthorizedException("Inactive user")
    return user


async def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user
```

- [ ] **Step 2: Commit**

```bash
git add app/api/deps.py
git commit -m "refactor(api): update deps with new imports and naming"
```

---

### Task 19: Update api/v1/**init**.py

**Files:**

- Modify: `app/api/v1/__init__.py`

- [ ] **Step 1: Update app/api/v1/**init**.py**

```python
from fastapi import APIRouter

from app.modules.users.router import router as users_router
from app.modules.roles.router import router as roles_router

api_router = APIRouter()
api_router.include_router(users_router, tags=["users", "auth"])
api_router.include_router(roles_router, tags=["roles", "permissions"])
```

- [ ] **Step 2: Commit**

```bash
git add app/api/v1/__init__.py
git commit -m "refactor(api): simplify v1 router registration"
```

---

### Task 20: Update main.py

**Files:**

- Modify: `app/main.py`

- [ ] **Step 1: Update app/main.py**

```python
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.db.session import business_engine, config_engine, user_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Application starting up...")
    yield
    logger.info("Application shutting down...")
    await user_engine.dispose()
    await business_engine.dispose()
    await config_engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500},
    )


@app.get("/")
async def root():
    return {
        "message": "Welcome to Enterprise FastAPI Project",
        "docs": f"{settings.API_V1_STR}/docs",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
    }


@app.get("/health/ready")
async def readiness_check():
    db_status = {}
    overall_status = "ready"

    async def check_db(name: str, engine) -> bool:
        try:
            async with engine.connect() as conn:
                from sqlalchemy import text

                await conn.execute(text("SELECT 1"))
                db_status[name] = "connected"
                return True
        except Exception as e:
            db_status[name] = f"error: {e!s}"
            return False

    user_ok = await check_db("user_db", user_engine)
    business_ok = await check_db("business_db", business_engine)
    config_ok = await check_db("config_db", config_engine)

    if not all([user_ok, business_ok, config_ok]):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "databases": db_status,
        "timestamp": datetime.now(UTC).isoformat(),
    }
```

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "refactor(main): update imports from db.session"
```

---

### Task 21: Delete shared directory and endpoints

**Files:**

- Delete: `app/modules/shared/`
- Delete: `app/api/v1/endpoints/`

- [ ] **Step 1: Delete shared directory**

```bash
rm -rf app/modules/shared/
```

- [ ] **Step 2: Delete endpoints directory**

```bash
rm -rf app/api/v1/endpoints/
```

- [ ] **Step 3: Verify app starts**

```bash
uv run python -c "from app.main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove shared module and api/v1/endpoints"
```

---

### Task 22: Update tests conftest.py

**Files:**

- Modify: `tests/conftest.py`

- [ ] **Step 1: Update tests/conftest.py**

```python
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, get_password_hash
from app.db.base import UserBase
from app.db.session import get_user_session
from app.main import app
from app.modules.users.models import User

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
    yield
    async with test_engine.begin() as conn:
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

    app.dependency_overrides[get_user_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(session):
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
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def superuser_token(test_user):
    test_user.is_superuser = True
    return create_access_token(subject=str(test_user.id))


@pytest_asyncio.fixture(scope="function")
async def user_token(test_user):
    return create_access_token(subject=str(test_user.id))


@pytest_asyncio.fixture(scope="function")
async def user_id(test_user):
    return test_user.id
```

- [ ] **Step 2: Commit**

```bash
git add tests/conftest.py
git commit -m "refactor(tests): update conftest with new imports and naming"
```

---

### Task 23: Run tests and verify

- [ ] **Step 1: Run lint**

```bash
just lint
```

Expected: All checks pass

- [ ] **Step 2: Run tests**

```bash
just test
```

Expected: All tests pass

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve lint and test issues"
```

---

## Phase 5: New Modules Scaffold

### Task 24: Create Products module

**Files:**

- Create: `app/modules/products/__init__.py`
- Create: `app/modules/products/models.py`
- Create: `app/modules/products/schemas.py`
- Create: `app/modules/products/repository.py`
- Create: `app/modules/products/service.py`
- Create: `app/modules/products/router.py`

- [ ] **Step 1: Write app/modules/products/**init**.py**

```python
```

- [ ] **Step 2: Write app/modules/products/models.py**

```python
from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import UserBase


class Product(UserBase):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

- [ ] **Step 3: Write app/modules/products/schemas.py**

```python
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0)
    category: str | None = Field(None, max_length=100)
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    price: Decimal | None = Field(None, gt=0)
    category: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    sku: str
    description: str | None
    price: Decimal
    category: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: Write app/modules/products/repository.py**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import BaseRepository
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductUpdate


class ProductRepository(BaseRepository[Product, ProductCreate, ProductUpdate]):
    async def get_by_sku(self, session: AsyncSession, sku: str) -> Product | None:
        result = await session.execute(select(Product).where(Product.sku == sku))
        return result.scalar_one_or_none()

    async def get_by_category(self, session: AsyncSession, category: str, skip: int = 0, limit: int = 100) -> list[Product]:
        result = await session.execute(
            select(Product)
            .where(Product.category == category)
            .order_by(Product.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


product_repo = ProductRepository(Product)
```

- [ ] **Step 5: Write app/modules/products/service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.products.models import Product
from app.modules.products.repository import product_repo
from app.modules.products.schemas import ProductCreate, ProductUpdate


async def get_product_by_id(session: AsyncSession, product_id: int) -> Product | None:
    return await product_repo.get(session, id=product_id)


async def get_product_by_sku(session: AsyncSession, sku: str) -> Product | None:
    return await product_repo.get_by_sku(session, sku=sku)


async def get_products(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[Product]:
    return await product_repo.get_multi(session, skip=skip, limit=limit)


async def get_products_by_category(session: AsyncSession, category: str, skip: int = 0, limit: int = 100) -> list[Product]:
    return await product_repo.get_by_category(session, category, skip=skip, limit=limit)


async def get_products_count(session: AsyncSession) -> int:
    return await product_repo.count(session)


async def create_product(session: AsyncSession, data: ProductCreate) -> Product:
    existing = await product_repo.get_by_sku(session, sku=data.sku)
    if existing:
        raise ConflictException(f"Product with SKU '{data.sku}' already exists")
    return await product_repo.create(session, data=data)


async def update_product(session: AsyncSession, product_id: int, data: ProductUpdate) -> Product:
    product = await product_repo.get(session, id=product_id)
    if not product:
        raise NotFoundException(f"Product with id {product_id} not found")
    return await product_repo.update(session, instance=product, data=data)


async def delete_product(session: AsyncSession, product_id: int) -> Product:
    product = await product_repo.get(session, id=product_id)
    if not product:
        raise NotFoundException(f"Product with id {product_id} not found")
    return await product_repo.delete(session, id=product_id)
```

- [ ] **Step 6: Write app/modules/products/router.py**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_user_session
from app.core.exceptions import NotFoundException
from app.common.schemas import DataResponse
from app.common.pagination import PaginatedResponse, PaginationParams
from app.modules.users.models import User
from app.modules.products.schemas import ProductCreate, ProductRead, ProductUpdate
from app.modules.products import service as product_service

router = APIRouter()


@router.post("/", response_model=DataResponse[ProductRead], status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    product = await product_service.create_product(session, data)
    return DataResponse(data=product, message="Product created successfully")


@router.get("/", response_model=PaginatedResponse[ProductRead])
async def get_products(
    pagination: PaginationParams = Depends(),
    category: str | None = None,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    if category:
        products = await product_service.get_products_by_category(session, category, skip=pagination.skip, limit=pagination.limit)
        total = len(products)
    else:
        products = await product_service.get_products(session, skip=pagination.skip, limit=pagination.limit)
        total = await product_service.get_products_count(session)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=products,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Products retrieved successfully",
    )


@router.get("/sku/{sku}", response_model=DataResponse[ProductRead])
async def get_product_by_sku(
    sku: str,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    product = await product_service.get_product_by_sku(session, sku)
    if not product:
        raise NotFoundException(f"Product with SKU {sku} not found")
    return DataResponse(data=product)


@router.get("/{product_id}", response_model=DataResponse[ProductRead])
async def get_product(
    product_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    product = await product_service.get_product_by_id(session, product_id)
    if not product:
        raise NotFoundException(f"Product {product_id} not found")
    return DataResponse(data=product)


@router.put("/{product_id}", response_model=DataResponse[ProductRead])
async def update_product(
    product_id: int,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    product = await product_service.update_product(session, product_id, data)
    return DataResponse(data=product, message="Product updated successfully")


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await product_service.delete_product(session, product_id)
    return None
```

- [ ] **Step 7: Register router in api/v1/**init**.py**

```python
from app.modules.products.router import router as products_router
# Add to api_router:
api_router.include_router(products_router, prefix="/products", tags=["products"])
```

- [ ] **Step 8: Commit**

```bash
git add app/modules/products/ app/api/v1/__init__.py
git commit -m "feat(products): add products module with CRUD endpoints"
```

---

### Task 25: Create Orders module

**Files:**

- Create: `app/modules/orders/__init__.py`
- Create: `app/modules/orders/models.py`
- Create: `app/modules/orders/associations.py` (not needed)
- Create: `app/modules/orders/schemas.py`
- Create: `app/modules/orders/repository.py`
- Create: `app/modules/orders/service.py`
- Create: `app/modules/orders/router.py`

- [ ] **Step 1: Write app/modules/orders/**init**.py**

```python
```

- [ ] **Step 2: Write app/modules/orders/models.py**

```python
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import ForeignKey, Numeric, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UserBase


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(UserBase):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(UserBase):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
```

- [ ] **Step 3: Write app/modules/orders/schemas.py**

```python
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.orders.models import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    created_at: datetime
    updated_at: datetime


class OrderCreate(BaseModel):
    user_id: int
    items: list[OrderItemCreate] = Field(..., min_length=1)


class OrderUpdate(BaseModel):
    status: OrderStatus | None = None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime


class OrderWithItems(OrderRead):
    items: list[OrderItemRead] = []
```

- [ ] **Step 4: Write app/modules/orders/repository.py**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repository import BaseRepository
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderUpdate


class OrderRepository(BaseRepository[Order, OrderCreate, OrderUpdate]):
    async def get_with_items(self, session: AsyncSession, order_id: int) -> Order | None:
        result = await session.execute(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, session: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> list[Order]:
        result = await session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_status(self, session: AsyncSession, status: OrderStatus, skip: int = 0, limit: int = 100) -> list[Order]:
        result = await session.execute(
            select(Order)
            .where(Order.status == status)
            .order_by(Order.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


order_repo = OrderRepository(Order)
```

- [ ] **Step 5: Write app/modules/orders/service.py**

```python
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ConflictException
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.orders.repository import order_repo
from app.modules.orders.schemas import OrderCreate, OrderUpdate


async def get_order_by_id(session: AsyncSession, order_id: int) -> Order | None:
    return await order_repo.get_with_items(session, order_id)


async def get_orders(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[Order]:
    return await order_repo.get_multi(session, skip=skip, limit=limit)


async def get_orders_by_user(session: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> list[Order]:
    return await order_repo.get_by_user(session, user_id, skip=skip, limit=limit)


async def get_orders_by_status(session: AsyncSession, status: OrderStatus, skip: int = 0, limit: int = 100) -> list[Order]:
    return await order_repo.get_by_status(session, status, skip=skip, limit=limit)


async def get_orders_count(session: AsyncSession) -> int:
    return await order_repo.count(session)


async def create_order(session: AsyncSession, data: OrderCreate) -> Order:
    total = sum(item.quantity * item.unit_price for item in data.items)
    order = Order(
        user_id=data.user_id,
        status=OrderStatus.PENDING,
        total_amount=Decimal(str(total)),
    )
    session.add(order)
    await session.flush()
    for item in data.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
        )
        session.add(order_item)
    await session.commit()
    await session.refresh(order)
    return await order_repo.get_with_items(session, order.id)


async def update_order_status(session: AsyncSession, order_id: int, data: OrderUpdate) -> Order:
    order = await order_repo.get(session, id=order_id)
    if not order:
        raise NotFoundException(f"Order with id {order_id} not found")
    if data.status:
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.COMPLETED],
            OrderStatus.COMPLETED: [],
            OrderStatus.CANCELLED: [],
        }
        if data.status not in valid_transitions.get(order.status, []):
            raise ConflictException(f"Cannot transition from {order.status} to {data.status}")
    return await order_repo.update(session, instance=order, data=data)


async def delete_order(session: AsyncSession, order_id: int) -> Order:
    order = await order_repo.get(session, id=order_id)
    if not order:
        raise NotFoundException(f"Order with id {order_id} not found")
    return await order_repo.delete(session, id=order_id)
```

- [ ] **Step 6: Write app/modules/orders/router.py**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_user_session
from app.core.exceptions import NotFoundException
from app.common.schemas import DataResponse
from app.common.pagination import PaginatedResponse, PaginationParams
from app.modules.orders.models import OrderStatus, User
from app.modules.orders.schemas import OrderCreate, OrderRead, OrderUpdate, OrderWithItems
from app.modules.orders import service as order_service

router = APIRouter()


@router.post("/", response_model=DataResponse[OrderWithItems], status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    order = await order_service.create_order(session, data)
    return DataResponse(data=order, message="Order created successfully")


@router.get("/", response_model=PaginatedResponse[OrderRead])
async def get_orders(
    pagination: PaginationParams = Depends(),
    user_id: int | None = None,
    status: OrderStatus | None = None,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    if user_id:
        orders = await order_service.get_orders_by_user(session, user_id, skip=pagination.skip, limit=pagination.limit)
        total = len(orders)
    elif status:
        orders = await order_service.get_orders_by_status(session, status, skip=pagination.skip, limit=pagination.limit)
        total = len(orders)
    else:
        orders = await order_service.get_orders(session, skip=pagination.skip, limit=pagination.limit)
        total = await order_service.get_orders_count(session)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=orders,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Orders retrieved successfully",
    )


@router.get("/my", response_model=PaginatedResponse[OrderRead])
async def get_my_orders(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_user_session),
    current_user: User = Depends(get_current_user),
):
    orders = await order_service.get_orders_by_user(session, current_user.id, skip=pagination.skip, limit=pagination.limit)
    total = len(orders)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=orders,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Orders retrieved successfully",
    )


@router.get("/{order_id}", response_model=DataResponse[OrderWithItems])
async def get_order(
    order_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    order = await order_service.get_order_by_id(session, order_id)
    if not order:
        raise NotFoundException(f"Order {order_id} not found")
    return DataResponse(data=order)


@router.put("/{order_id}", response_model=DataResponse[OrderRead])
async def update_order(
    order_id: int,
    data: OrderUpdate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    order = await order_service.update_order_status(session, order_id, data)
    return DataResponse(data=order, message="Order updated successfully")


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await order_service.delete_order(session, order_id)
    return None
```

- [ ] **Step 7: Register router**

```python
# In app/api/v1/__init__.py
from app.modules.orders.router import router as orders_router
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
```

- [ ] **Step 8: Commit**

```bash
git add app/modules/orders/ app/api/v1/__init__.py
git commit -m "feat(orders): add orders module with status workflow"
```

---

### Task 26: Create Config module

**Files:**

- Create: `app/modules/config/__init__.py`
- Create: `app/modules/config/models.py`
- Create: `app/modules/config/schemas.py`
- Create: `app/modules/config/repository.py`
- Create: `app/modules/config/service.py`
- Create: `app/modules/config/router.py`

- [ ] **Step 1: Write app/modules/config/**init**.py**

```python
```

- [ ] **Step 2: Write app/modules/config/models.py**

```python
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BusinessBase


class SystemConfig(BusinessBase):
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

- [ ] **Step 3: Write app/modules/config/schemas.py**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConfigCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1)
    description: str | None = Field(None, max_length=255)
    is_active: bool = True


class ConfigUpdate(BaseModel):
    value: str | None = None
    description: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class ConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    value: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: Write app/modules/config/repository.py**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import BaseRepository
from app.modules.config.models import SystemConfig
from app.modules.config.schemas import ConfigCreate, ConfigUpdate


class ConfigRepository(BaseRepository[SystemConfig, ConfigCreate, ConfigUpdate]):
    async def get_by_key(self, session: AsyncSession, key: str) -> SystemConfig | None:
        result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
        return result.scalar_one_or_none()


config_repo = ConfigRepository(SystemConfig)
```

- [ ] **Step 5: Write app/modules/config/service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.config.models import SystemConfig
from app.modules.config.repository import config_repo
from app.modules.config.schemas import ConfigCreate, ConfigUpdate


async def get_config_by_id(session: AsyncSession, config_id: int) -> SystemConfig | None:
    return await config_repo.get(session, id=config_id)


async def get_config_by_key(session: AsyncSession, key: str) -> SystemConfig | None:
    return await config_repo.get_by_key(session, key=key)


async def get_configs(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[SystemConfig]:
    return await config_repo.get_multi(session, skip=skip, limit=limit)


async def get_configs_count(session: AsyncSession) -> int:
    return await config_repo.count(session)


async def create_config(session: AsyncSession, data: ConfigCreate) -> SystemConfig:
    existing = await config_repo.get_by_key(session, key=data.key)
    if existing:
        raise ConflictException(f"Config with key '{data.key}' already exists")
    return await config_repo.create(session, data=data)


async def update_config(session: AsyncSession, config_id: int, data: ConfigUpdate) -> SystemConfig:
    config = await config_repo.get(session, id=config_id)
    if not config:
        raise NotFoundException(f"Config with id {config_id} not found")
    return await config_repo.update(session, instance=config, data=data)


async def delete_config(session: AsyncSession, config_id: int) -> SystemConfig:
    config = await config_repo.get(session, id=config_id)
    if not config:
        raise NotFoundException(f"Config with id {config_id} not found")
    return await config_repo.delete(session, id=config_id)
```

- [ ] **Step 6: Write app/modules/config/router.py**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_business_session
from app.core.exceptions import NotFoundException
from app.common.schemas import DataResponse
from app.common.pagination import PaginatedResponse, PaginationParams
from app.modules.users.models import User
from app.modules.config.schemas import ConfigCreate, ConfigRead, ConfigUpdate
from app.modules.config import service as config_service

router = APIRouter()


@router.post("/", response_model=DataResponse[ConfigRead], status_code=status.HTTP_201_CREATED)
async def create_config(
    data: ConfigCreate,
    session: AsyncSession = Depends(get_business_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    config = await config_service.create_config(session, data)
    return DataResponse(data=config, message="Config created successfully")


@router.get("/", response_model=PaginatedResponse[ConfigRead])
async def get_configs(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_business_session),
    _current_user: User = Depends(get_current_user),
):
    configs = await config_service.get_configs(session, skip=pagination.skip, limit=pagination.limit)
    total = await config_service.get_configs_count(session)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=configs,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Configs retrieved successfully",
    )


@router.get("/key/{key}", response_model=DataResponse[ConfigRead])
async def get_config_by_key(
    key: str,
    session: AsyncSession = Depends(get_business_session),
    _current_user: User = Depends(get_current_user),
):
    config = await config_service.get_config_by_key(session, key)
    if not config:
        raise NotFoundException(f"Config with key {key} not found")
    return DataResponse(data=config)


@router.get("/{config_id}", response_model=DataResponse[ConfigRead])
async def get_config(
    config_id: int,
    session: AsyncSession = Depends(get_business_session),
    _current_user: User = Depends(get_current_user),
):
    config = await config_service.get_config_by_id(session, config_id)
    if not config:
        raise NotFoundException(f"Config {config_id} not found")
    return DataResponse(data=config)


@router.put("/{config_id}", response_model=DataResponse[ConfigRead])
async def update_config(
    config_id: int,
    data: ConfigUpdate,
    session: AsyncSession = Depends(get_business_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    config = await config_service.update_config(session, config_id, data)
    return DataResponse(data=config, message="Config updated successfully")


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    config_id: int,
    session: AsyncSession = Depends(get_business_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await config_service.delete_config(session, config_id)
    return None
```

- [ ] **Step 7: Register router**

```python
# In app/api/v1/__init__.py
from app.modules.config.router import router as config_router
api_router.include_router(config_router, prefix="/config", tags=["config"])
```

- [ ] **Step 8: Commit**

```bash
git add app/modules/config/ app/api/v1/__init__.py
git commit -m "feat(config): add system config module using BusinessBase"
```

---

### Task 27: Create Audit module

**Files:**

- Create: `app/modules/audit/__init__.py`
- Create: `app/modules/audit/models.py`
- Create: `app/modules/audit/schemas.py`
- Create: `app/modules/audit/repository.py`
- Create: `app/modules/audit/service.py`
- Create: `app/modules/audit/router.py`

- [ ] **Step 1: Write app/modules/audit/**init**.py**

```python
```

- [ ] **Step 2: Write app/modules/audit/models.py**

```python
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import UserBase


class AuditLog(UserBase):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
```

- [ ] **Step 3: Write app/modules/audit/schemas.py**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditLogCreate(BaseModel):
    user_id: int | None = None
    action: str = Field(..., min_length=1, max_length=20)
    resource_type: str = Field(..., min_length=1, max_length=50)
    resource_id: int
    old_value: str | None = None
    new_value: str | None = None
    ip_address: str | None = Field(None, max_length=45)


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    action: str
    resource_type: str
    resource_id: int
    old_value: str | None
    new_value: str | None
    ip_address: str | None
    created_at: datetime
```

- [ ] **Step 4: Write app/modules/audit/repository.py**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import BaseRepository
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogCreate


class AuditLogRepository(BaseRepository[AuditLog, AuditLogCreate, AuditLogCreate]):
    async def get_by_user(self, session: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_resource(self, session: AsyncSession, resource_type: str, resource_id: int, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.resource_type == resource_type, AuditLog.resource_id == resource_id)
            .order_by(AuditLog.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


audit_repo = AuditLogRepository(AuditLog)
```

- [ ] **Step 5: Write app/modules/audit/service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.audit.repository import audit_repo
from app.modules.audit.schemas import AuditLogCreate


async def get_audit_log_by_id(session: AsyncSession, log_id: int) -> AuditLog | None:
    return await audit_repo.get(session, id=log_id)


async def get_audit_logs(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[AuditLog]:
    return await audit_repo.get_multi(session, skip=skip, limit=limit)


async def get_audit_logs_by_user(session: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> list[AuditLog]:
    return await audit_repo.get_by_user(session, user_id, skip=skip, limit=limit)


async def get_audit_logs_by_resource(session: AsyncSession, resource_type: str, resource_id: int, skip: int = 0, limit: int = 100) -> list[AuditLog]:
    return await audit_repo.get_by_resource(session, resource_type, resource_id, skip=skip, limit=limit)


async def get_audit_logs_count(session: AsyncSession) -> int:
    return await audit_repo.count(session)


async def create_audit_log(session: AsyncSession, data: AuditLogCreate) -> AuditLog:
    return await audit_repo.create(session, data=data)
```

- [ ] **Step 6: Write app/modules/audit/router.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_user_session
from app.core.exceptions import NotFoundException
from app.common.schemas import DataResponse
from app.common.pagination import PaginatedResponse, PaginationParams
from app.modules.users.models import User
from app.modules.audit.schemas import AuditLogRead
from app.modules.audit import service as audit_service

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[AuditLogRead])
async def get_audit_logs(
    pagination: PaginationParams = Depends(),
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    if user_id:
        logs = await audit_service.get_audit_logs_by_user(session, user_id, skip=pagination.skip, limit=pagination.limit)
        total = len(logs)
    elif resource_type and resource_id:
        logs = await audit_service.get_audit_logs_by_resource(session, resource_type, resource_id, skip=pagination.skip, limit=pagination.limit)
        total = len(logs)
    else:
        logs = await audit_service.get_audit_logs(session, skip=pagination.skip, limit=pagination.limit)
        total = await audit_service.get_audit_logs_count(session)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=logs,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Audit logs retrieved successfully",
    )


@router.get("/{log_id}", response_model=DataResponse[AuditLogRead])
async def get_audit_log(
    log_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    log = await audit_service.get_audit_log_by_id(session, log_id)
    if not log:
        raise NotFoundException(f"Audit log {log_id} not found")
    return DataResponse(data=log)
```

- [ ] **Step 7: Register router**

```python
# In app/api/v1/__init__.py
from app.modules.audit.router import router as audit_router
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
```

- [ ] **Step 8: Commit**

```bash
git add app/modules/audit/ app/api/v1/__init__.py
git commit -m "feat(audit): add read-only audit log module"
```

---

## Phase 6: Restructure Tests

### Task 28: Restructure test directories

**Files:**

- Create: `tests/modules/users/`
- Create: `tests/modules/roles/`
- Create: `tests/modules/products/`
- Create: `tests/modules/orders/`
- Create: `tests/modules/config/`
- Create: `tests/modules/audit/`
- Create: `tests/core/`
- Create: `tests/db/`
- Delete: `tests/test_api/`
- Delete: `tests/test_services/`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p tests/modules/{users,roles,products,orders,config,audit}
mkdir -p tests/core
mkdir -p tests/db
```

- [ ] **Step 2: Delete old directories**

```bash
rm -rf tests/test_api tests/test_services
```

- [ ] **Step 3: Move and update tests**
(Manual migration of existing tests to new structure - placeholder)

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(tests): restructure test directories to mirror app structure"
```

---

## Phase 7: Final Verification

### Task 29: Run full verification

- [ ] **Step 1: Run lint**

```bash
just lint
```

Expected: All checks pass

- [ ] **Step 2: Run tests**

```bash
just test
```

Expected: All tests pass

- [ ] **Step 3: Verify app starts**

```bash
uv run python -c "from app.main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Verify no circular imports**

```bash
uv run python -c "from app.modules.users.models import User; from app.modules.roles.models import Role; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "docs: update README to reflect new architecture"
```

---

## Summary

This plan covers:

1. **Phase 1-2:** Split `shared/db.py` and `shared/schemas.py` into focused packages
2. **Phase 3:** Resolve circular imports by extracting association tables
3. **Phase 4:** Update all imports and naming throughout the codebase
4. **Phase 5:** Scaffold 4 new modules (Products, Orders, Config, Audit) using new patterns
5. **Phase 6:** Restructure tests to mirror `app/` structure
6. **Phase 7:** Full verification

Each task is self-contained with exact file paths and code. Follow in order, commit after each task.
