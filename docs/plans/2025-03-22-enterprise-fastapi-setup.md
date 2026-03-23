# Enterprise FastAPI Project Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建一个企业级FastAPI项目，包含清晰的目录结构（apis, core, models, crud, schemas, services, tests），全部使用异步操作，数据库使用SQL Server。

**Architecture:** 
- 采用分层架构：API层 → Service层 → CRUD层 → Model层
- 使用SQLAlchemy 2.0 + aiosqlite/asyncpg进行异步数据库操作
- 通过pymssql或pyodbc支持SQL Server连接
- 使用Pydantic V2进行数据验证和序列化

**Tech Stack:**
- FastAPI + Uvicorn (异步ASGI服务器)
- SQLAlchemy 2.0 + async/await
- SQL Server (通过aiomssql或异步驱动)
- Pydantic V2
- Alembic (数据库迁移)
- Pytest + Async test support

---

## 目录结构

```
.
├── alembic/                    # 数据库迁移目录
│   ├── versions/               # 迁移版本文件
│   └── env.py                  # Alembic环境配置
├── app/                        # 主应用目录
│   ├── __init__.py
│   ├── main.py                 # FastAPI应用入口
│   ├── api/                    # API路由层
│   │   ├── __init__.py
│   │   ├── deps.py             # 依赖注入
│   │   └── v1/                 # API版本1
│   │       ├── __init__.py
│   │       └── endpoints/      # 端点模块
│   │           ├── __init__.py
│   │           └── users.py    # 用户端点示例
│   ├── core/                   # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py           # 配置管理
│   │   ├── security.py         # 安全工具
│   │   └── exceptions.py       # 自定义异常
│   ├── models/                 # 数据库模型层
│   │   ├── __init__.py
│   │   └── user.py             # 用户模型示例
│   ├── schemas/                # Pydantic模型层
│   │   ├── __init__.py
│   │   ├── user.py             # 用户Schema
│   │   └── common.py           # 通用Schema
│   ├── crud/                   # CRUD操作层
│   │   ├── __init__.py
│   │   ├── base.py             # 基础CRUD类
│   │   └── user.py             # 用户CRUD
│   ├── services/               # 业务逻辑层
│   │   ├── __init__.py
│   │   └── user.py             # 用户服务
│   └── db/                     # 数据库配置
│       ├── __init__.py
│       ├── session.py          # 异步会话管理
│       └── base.py             # 基础模型
├── tests/                      # 测试目录
│   ├── __init__.py
│   ├── conftest.py             # Pytest配置
│   ├── test_api/               # API测试
│   │   └── test_users.py
│   └── test_services/          # 服务测试
│       └── test_user_service.py
├── .env.example                # 环境变量示例
├── alembic.ini                 # Alembic配置
├── requirements.txt            # 依赖文件
└── pytest.ini                  # Pytest配置
```

---

## Task 1: 创建项目基础结构和依赖配置

**Files:**
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `alembic.ini`
- Create: 所有目录结构

**Step 1: 创建依赖文件 requirements.txt**

```txt
# FastAPI
fastapi==0.110.0
uvicorn[standard]==0.27.1

# Async Database
sqlalchemy[asyncio]==2.0.27
asyncpg==0.29.0
aiomysql==0.2.0
pymssql==2.2.11
pyodbc==5.1.0

# Migration
alembic==1.13.1

# Data validation
pydantic==2.6.1
pydantic-settings==2.1.0

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Testing
pytest==8.0.0
pytest-asyncio==0.23.5
httpx==0.26.0

# Development
python-dotenv==1.0.0
```

**Step 2: 创建环境变量示例文件 .env.example**

```bash
# Application
APP_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production

# Database - SQL Server
DATABASE_URL=mssql+aioodbc://username:password@host:port/dbname?driver=ODBC+Driver+17+for+SQL+Server
# Alternative: mssql+pytds://username:password@host:port/dbname

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]

# Logging
LOG_LEVEL=INFO
```

**Step 3: 创建Pytest配置 pytest.ini**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
```

**Step 4: 创建Alembic配置 alembic.ini**

```ini
# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = alembic

# template used to generate migration file names; The default value is %%(rev)s_%%(slug)s
# Uncomment the line below if you want the files to be prepended with date and time
# file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the python>=3.9 or backports.zoneinfo library.
# Any required deps can installed by adding `alembic[tz]` to the pip requirements
# string value is passed to ZoneInfo()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version location specification; This defaults
# to alembic/versions.  When using multiple version
# directories, initial revisions must be specified with --version-path.
# The path separator used here should be the separator specified by "version_locations" below.
# version_locations = %(here)s/bar:%(here)s/bat:alembic/versions

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

sqlalchemy.url = driver://user:pass@localhost/dbname


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

# lint with attempts to fix using "ruff" - use the exec runner, execute a binary
# hooks = ruff
# ruff.type = exec
# ruff.executable = %(here)s/.venv/bin/ruff
# ruff.options = --fix REVISION_SCRIPT_FILENAME

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

**Step 5: 创建目录结构**

```bash
mkdir -p app/api/v1/endpoints
mkdir -p app/core
mkdir -p app/models
mkdir -p app/schemas
mkdir -p app/crud
mkdir -p app/services
mkdir -p app/db
mkdir -p alembic/versions
mkdir -p tests/test_api
mkdir -p tests/test_services
```

**Step 6: Commit**

```bash
git add .
git commit -m "chore: initialize project structure with dependencies"
```

---

## Task 2: 创建核心配置模块 (core/)

**Files:**
- Create: `app/__init__.py`
- Create: `app/core/__init__.py`
- Create: `app/core/config.py`
- Create: `app/core/exceptions.py`
- Create: `app/core/security.py`

**Step 1: 创建核心配置 app/core/config.py**

```python
from typing import List, Optional, Union
from pydantic import field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # Database
    DATABASE_URL: str
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Enterprise FastAPI Project"
    
    # Token
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days


settings = Settings()
```

**Step 2: 创建异常定义 app/core/exceptions.py**

```python
from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Base API Exception"""
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundException(BaseAPIException):
    """Resource not found"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictException(BaseAPIException):
    """Resource conflict"""
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnauthorizedException(BaseAPIException):
    """Unauthorized access"""
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(BaseAPIException):
    """Forbidden access"""
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ValidationException(BaseAPIException):
    """Validation error"""
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
```

**Step 3: 创建安全工具 app/core/security.py**

```python
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(
    subject: Union[str, int], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and return subject"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)
```

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add core configuration, security, and exceptions"
```

---

## Task 3: 创建数据库基础模块 (db/)

**Files:**
- Create: `app/db/__init__.py`
- Create: `app/db/base.py`
- Create: `app/db/session.py`

**Step 1: 创建基础模型类 app/db/base.py**

```python
from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models"""
    
    # Generate __tablename__ automatically from class name
    @classmethod
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # Common columns for all tables
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
```

**Step 2: 创建异步会话管理 app/db/session.py**

```python
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker,
    AsyncEngine
)

from app.core.config import settings

# Create async engine for SQL Server
# Note: For SQL Server, you might need to adjust the driver string
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncSession:
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database - create tables"""
    from app.db.base import Base
    from app.models import user  # Import all models
    
    async with engine.begin() as conn:
        # In production, use Alembic migrations instead
        if settings.DEBUG:
            await conn.run_sync(Base.metadata.create_all)
```

**Step 3: Commit**

```bash
git add .
git commit -m "feat: add async database base classes and session management"
```

---

## Task 4: 创建数据模型 (models/)

**Files:**
- Create: `app/models/__init__.py`
- Create: `app/models/user.py`

**Step 1: 创建用户模型 app/models/user.py**

```python
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """User database model"""
    
    # Override table name
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True, 
        nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(100), 
        unique=True, 
        index=True, 
        nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
```

**Step 2: 更新模型模块 app/models/__init__.py**

```python
from app.models.user import User

__all__ = ["User"]
```

**Step 3: Commit**

```bash
git add .
git commit -m "feat: add User database model"
```

---

## Task 5: 创建Pydantic Schema (schemas/)

**Files:**
- Create: `app/schemas/__init__.py`
- Create: `app/schemas/common.py`
- Create: `app/schemas/user.py`

**Step 1: 创建通用Schema app/schemas/common.py**

```python
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar("T")


class ResponseBase(BaseModel):
    """Base response model"""
    success: bool = True
    message: Optional[str] = None


class DataResponse(ResponseBase, Generic[T]):
    """Response with data"""
    data: T


class ListResponse(ResponseBase, Generic[T]):
    """Response with list data"""
    data: List[T]


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = 1
    page_size: int = 10
    
    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(ListResponse[T], Generic[T]):
    """Paginated response"""
    total: int
    page: int
    page_size: int
    total_pages: int
```

**Step 2: 创建用户Schema app/schemas/user.py**

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


# Shared properties
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool = True


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str


# Properties to receive via API on update
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


# Properties stored in DB
class UserInDB(UserBase):
    id: int
    hashed_password: str
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Properties to return via API
class UserResponse(UserBase):
    id: int
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Properties for authentication
class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
```

**Step 3: 更新Schema模块 app/schemas/__init__.py**

```python
from app.schemas.common import (
    ResponseBase,
    DataResponse,
    ListResponse,
    PaginationParams,
    PaginatedResponse,
)
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserInDB,
    UserResponse,
    UserLogin,
    Token,
    TokenPayload,
)

__all__ = [
    # Common
    "ResponseBase",
    "DataResponse", 
    "ListResponse",
    "PaginationParams",
    "PaginatedResponse",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenPayload",
]
```

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add Pydantic schemas for validation and serialization"
```

---

## Task 6: 创建CRUD基础层 (crud/)

**Files:**
- Create: `app/crud/__init__.py`
- Create: `app/crud/base.py`
- Create: `app/crud/user.py`

**Step 1: 创建基础CRUD类 app/crud/base.py**

```python
from typing import Generic, TypeVar, Optional, List, Dict, Any, Sequence
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base CRUD class with async operations"""
    
    def __init__(self, model: type[ModelType]):
        """
        CRUD object with default async methods to Create, Read, Update, Delete
        
        Args:
            model: A SQLAlchemy model class
        """
        self.model = model
    
    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """Get single item by ID"""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> Sequence[ModelType]:
        """Get multiple items with pagination"""
        result = await db.execute(
            select(self.model)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def count(self, db: AsyncSession) -> int:
        """Get total count"""
        result = await db.execute(select(func.count()).select_from(self.model))
        return result.scalar()
    
    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create new item"""
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        db_obj: ModelType, 
        obj_in: UpdateSchemaType | Dict[str, Any]
    ) -> ModelType:
        """Update item"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """Delete item"""
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
```

**Step 2: 创建用户CRUD app/crud/user.py**

```python
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get user by email"""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        """Get user by username"""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create user with hashed password"""
        db_obj = User(
            email=obj_in.email,
            username=obj_in.username,
            full_name=obj_in.full_name,
            hashed_password=get_password_hash(obj_in.password),
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def authenticate(
        self, 
        db: AsyncSession, 
        *, 
        username: str, 
        password: str
    ) -> Optional[User]:
        """Authenticate user"""
        user = await self.get_by_username(db, username=username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    async def is_active(self, user: User) -> bool:
        """Check if user is active"""
        return user.is_active
    
    async def is_superuser(self, user: User) -> bool:
        """Check if user is superuser"""
        return user.is_superuser


user = CRUDUser(User)
```

**Step 3: 更新CRUD模块 app/crud/__init__.py**

```python
from app.crud.user import user
from app.crud.base import CRUDBase

__all__ = ["user", "CRUDBase"]
```

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add async CRUD base class and User CRUD operations"
```

---

## Task 7: 创建业务服务层 (services/)

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/user.py`

**Step 1: 创建用户服务 app/services/user.py**

```python
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ConflictException
from app.core.security import create_access_token
from app.crud.user import user as user_crud
from app.models.user import User
from app.schemas.user import (
    UserCreate, 
    UserUpdate, 
    UserResponse,
    Token
)


class UserService:
    """User business logic service"""
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID"""
        user = await user_crud.get(db, id=user_id)
        return user
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email"""
        return await user_crud.get_by_email(db, email=email)
    
    @staticmethod
    async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users list"""
        users = await user_crud.get_multi(db, skip=skip, limit=limit)
        return list(users)
    
    @staticmethod
    async def get_users_count(db: AsyncSession) -> int:
        """Get total users count"""
        return await user_crud.count(db)
    
    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
        """Create new user"""
        # Check if email already exists
        existing_user = await user_crud.get_by_email(db, email=user_in.email)
        if existing_user:
            raise ConflictException(f"Email {user_in.email} already registered")
        
        # Check if username already exists
        existing_user = await user_crud.get_by_username(db, username=user_in.username)
        if existing_user:
            raise ConflictException(f"Username {user_in.username} already taken")
        
        return await user_crud.create(db, obj_in=user_in)
    
    @staticmethod
    async def update_user(
        db: AsyncSession, 
        user_id: int, 
        user_in: UserUpdate
    ) -> User:
        """Update user"""
        user = await user_crud.get(db, id=user_id)
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        
        # Check email uniqueness if being updated
        if user_in.email and user_in.email != user.email:
            existing_user = await user_crud.get_by_email(db, email=user_in.email)
            if existing_user:
                raise ConflictException(f"Email {user_in.email} already registered")
        
        # Check username uniqueness if being updated
        if user_in.username and user_in.username != user.username:
            existing_user = await user_crud.get_by_username(db, username=user_in.username)
            if existing_user:
                raise ConflictException(f"Username {user_in.username} already taken")
        
        return await user_crud.update(db, db_obj=user, obj_in=user_in)
    
    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int) -> User:
        """Delete user"""
        user = await user_crud.get(db, id=user_id)
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        
        return await user_crud.delete(db, id=user_id)
    
    @staticmethod
    async def authenticate_user(
        db: AsyncSession, 
        username: str, 
        password: str
    ) -> Optional[User]:
        """Authenticate user"""
        return await user_crud.authenticate(db, username=username, password=password)
    
    @staticmethod
    async def login_user(db: AsyncSession, username: str, password: str) -> Token:
        """Login user and return token"""
        user = await UserService.authenticate_user(db, username, password)
        if not user:
            raise NotFoundException("Invalid credentials")
        if not user.is_active:
            raise NotFoundException("Inactive user")
        
        access_token = create_access_token(subject=str(user.id))
        return Token(access_token=access_token)


user_service = UserService()
```

**Step 2: 更新服务模块 app/services/__init__.py**

```python
from app.services.user import UserService, user_service

__all__ = ["UserService", "user_service"]
```

**Step 3: Commit**

```bash
git add .
git commit -m "feat: add User service layer with business logic"
```

---

## Task 8: 创建API路由层 (api/)

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/v1/__init__.py`
- Create: `app/api/v1/endpoints/__init__.py`
- Create: `app/api/v1/endpoints/users.py`
- Create: `app/api/deps.py`

**Step 1: 创建依赖注入 app/api/deps.py**

```python
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.security import verify_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.crud.user import user as user_crud

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_db() -> AsyncSession:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get current authenticated user"""
    user_id = verify_token(token)
    if user_id is None:
        raise UnauthorizedException("Could not validate credentials")
    
    user = await user_crud.get(db, id=int(user_id))
    if user is None:
        raise UnauthorizedException("User not found")
    if not user.is_active:
        raise UnauthorizedException("Inactive user")
    
    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
```

**Step 2: 创建用户端点 app/api/v1/endpoints/users.py**

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_current_active_superuser
from app.core.exceptions import NotFoundException
from app.schemas.user import (
    UserCreate, 
    UserUpdate, 
    UserResponse, 
    UserLogin,
    Token
)
from app.schemas.common import DataResponse, ListResponse, PaginatedResponse, PaginationParams
from app.services.user import user_service
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=DataResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register new user"""
    user = await user_service.create_user(db, user_in)
    return DataResponse(data=user, message="User created successfully")


@router.post("/login", response_model=DataResponse[Token])
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """User login"""
    token = await user_service.login_user(
        db, 
        username=credentials.username, 
        password=credentials.password
    )
    return DataResponse(data=token, message="Login successful")


@router.get("/me", response_model=DataResponse[UserResponse])
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Get current user"""
    return DataResponse(data=current_user)


@router.get("/{user_id}", response_model=DataResponse[UserResponse])
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user by ID"""
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException(f"User {user_id} not found")
    return DataResponse(data=user)


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def get_users(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """Get users list (superuser only)"""
    users = await user_service.get_users(
        db, 
        skip=pagination.skip, 
        limit=pagination.limit
    )
    total = await user_service.get_users_count(db)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        data=list(users),
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Users retrieved successfully"
    )


@router.put("/{user_id}", response_model=DataResponse[UserResponse])
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user"""
    # Users can only update themselves unless superuser
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = await user_service.update_user(db, user_id, user_in)
    return DataResponse(data=user, message="User updated successfully")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """Delete user (superuser only)"""
    await user_service.delete_user(db, user_id)
    return None
```

**Step 3: 创建API路由模块 app/api/v1/__init__.py**

```python
from fastapi import APIRouter

from app.api.v1.endpoints import users

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(users.router, prefix="/auth", tags=["auth"])
```

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add API endpoints with authentication and authorization"
```

---

## Task 9: 创建FastAPI主应用 (main.py)

**Files:**
- Create: `app/main.py`

**Step 1: 创建主应用文件 app/main.py**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import api_router
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print(f"Starting {settings.PROJECT_NAME}...")
    # Initialize database (in production, use Alembic migrations)
    # await init_db()
    yield
    # Shutdown
    print(f"Shutting down {settings.PROJECT_NAME}...")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Configure CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Enterprise FastAPI Project",
        "docs": f"{settings.API_V1_STR}/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
```

**Step 2: Commit**

```bash
git add .
git commit -m "feat: add FastAPI main application with lifespan and CORS"
```

---

## Task 10: 创建Alembic迁移配置

**Files:**
- Create: `alembic/__init__.py`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`

**Step 1: 创建Alembic环境配置 alembic/env.py**

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import engine

from alembic import context

from app.core.config import settings
from app.db.base import Base
from app.models import user  # Import all models

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Override sqlalchemy.url with our settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations"""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 2: 创建Alembic脚本模板 alembic/script.py.mako**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

**Step 3: Commit**

```bash
git add .
git commit -m "chore: add Alembic async migration configuration"
```

---

## Task 11: 创建测试基础设施

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_api/__init__.py`
- Create: `tests/test_services/__init__.py`

**Step 1: 创建Pytest配置 tests/conftest.py**

```python
import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.api.deps import get_db

# Test database URL (use SQLite in memory for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    future=True,
)

# Create test session factory
TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Setup test database"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Get database session for tests"""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session):
    """Get test client"""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
```

**Step 2: Commit**

```bash
git add .
git commit -m "test: add pytest configuration with async test support"
```

---

## Task 12: 创建API测试

**Files:**
- Create: `tests/test_api/test_users.py`

**Step 1: 创建用户API测试 tests/test_api/test_users.py**

```python
import pytest
from fastapi import status


@pytest.mark.asyncio
class TestUserRegistration:
    """Test user registration endpoints"""
    
    async def test_register_success(self, client):
        """Test successful user registration"""
        response = await client.post(
            "/api/v1/users/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "full_name": "Test User",
                "password": "testpassword123",
                "is_active": True
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == "test@example.com"
        assert data["data"]["username"] == "testuser"
        assert "password" not in data["data"]
    
    async def test_register_duplicate_email(self, client):
        """Test registration with duplicate email"""
        # Create first user
        await client.post(
            "/api/v1/users/register",
            json={
                "email": "duplicate@example.com",
                "username": "user1",
                "password": "testpassword123",
            }
        )
        
        # Try to create second user with same email
        response = await client.post(
            "/api/v1/users/register",
            json={
                "email": "duplicate@example.com",
                "username": "user2",
                "password": "testpassword123",
            }
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
class TestUserLogin:
    """Test user login endpoints"""
    
    async def test_login_success(self, client):
        """Test successful login"""
        # Create user first
        await client.post(
            "/api/v1/users/register",
            json={
                "email": "login@example.com",
                "username": "logintest",
                "password": "testpassword123",
            }
        )
        
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "logintest",
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
    
    async def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
class TestGetCurrentUser:
    """Test getting current user"""
    
    async def test_get_me_authenticated(self, client):
        """Test get current user when authenticated"""
        # Create and login user
        await client.post(
            "/api/v1/users/register",
            json={
                "email": "me@example.com",
                "username": "metest",
                "password": "testpassword123",
            }
        )
        
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "metest",
                "password": "testpassword123"
            }
        )
        
        token = login_response.json()["data"]["access_token"]
        
        # Get current user
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["email"] == "me@example.com"


class TestHealthCheck:
    """Test health check endpoint"""
    
    async def test_health_check(self, client):
        """Test health check returns healthy"""
        response = await client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
```

**Step 2: Commit**

```bash
git add .
git commit -m "test: add user API tests with async support"
```

---

## Task 13: 创建启动脚本和文档

**Files:**
- Create: `run.py`
- Create: `README.md`

**Step 1: 创建启动脚本 run.py**

```python
import uvicorn
from app.core.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4,
    )
```

**Step 2: 创建README文档 README.md**

```markdown
# Enterprise FastAPI Project

企业级FastAPI项目模板，使用异步操作和分层架构。

## 项目结构

```
.
├── alembic/              # 数据库迁移
├── app/                  # 主应用目录
│   ├── api/              # API路由层
│   ├── core/             # 核心配置
│   ├── crud/             # CRUD操作层
│   ├── db/               # 数据库配置
│   ├── models/           # 数据库模型
│   ├── schemas/          # Pydantic模型
│   ├── services/         # 业务逻辑层
│   └── main.py           # 应用入口
├── tests/                # 测试目录
├── requirements.txt      # 依赖
└── README.md            # 项目文档
```

## 技术栈

- **FastAPI**: 高性能异步Web框架
- **SQLAlchemy 2.0**: ORM工具，支持异步操作
- **Pydantic V2**: 数据验证和序列化
- **Alembic**: 数据库迁移
- **Pytest**: 异步测试框架
- **SQL Server**: 企业级关系数据库

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 3. 配置SQL Server连接

编辑 `.env` 文件，设置数据库连接：

```bash
DATABASE_URL=mssql+aioodbc://username:password@host:port/dbname?driver=ODBC+Driver+17+for+SQL+Server
```

### 4. 运行数据库迁移

```bash
alembic upgrade head
```

### 5. 启动应用

```bash
# 开发模式
python run.py

# 或使用uvicorn
uvicorn app.main:app --reload
```

## API文档

启动后访问：
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 运行测试

```bash
pytest
```

## 架构说明

### 分层架构

1. **API Layer** (`app/api/`): 处理HTTP请求和响应
2. **Service Layer** (`app/services/`): 业务逻辑
3. **CRUD Layer** (`app/crud/`): 数据库访问
4. **Model Layer** (`app/models/`): 数据模型定义
5. **Schema Layer** (`app/schemas/`): 数据验证

### 异步支持

所有数据库操作使用异步SQLAlchemy：
- 异步引擎创建: `create_async_engine`
- 异步会话: `AsyncSession`
- 异步CRUD: `await crud.get()`, `await crud.create()`
- 异步服务: `await service.create_user()`

## 开发指南

### 添加新资源

1. 创建模型 (`app/models/`)
2. 创建Schema (`app/schemas/`)
3. 创建CRUD (`app/crud/`)
4. 创建服务 (`app/services/`)
5. 创建API端点 (`app/api/v1/endpoints/`)
6. 添加测试 (`tests/`)

### 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## License

MIT
```

**Step 3: Commit**

```bash
git add .
git commit -m "docs: add README and run script"
```

---

## Task 14: 创建空白__init__.py文件

**Files:**
- Create: All missing `__init__.py` files

**Step 1: 创建所有空的__init__.py文件**

需要创建的文件：
- `app/__init__.py`
- `app/api/__init__.py`
- `app/api/v1/__init__.py`
- `app/api/v1/endpoints/__init__.py`
- `alembic/__init__.py`
- `tests/__init__.py`
- `tests/test_api/__init__.py`
- `tests/test_services/__init__.py`

每个文件内容为空或添加注释：

```python
# Initialize module
```

**Step 2: Commit**

```bash
git add .
git commit -m "chore: add __init__.py files for all modules"
```

---

## 总结

企业级FastAPI项目结构已设计完成，包含：

✅ **清晰的目录分层**: apis, core, models, crud, schemas, services, tests
✅ **全异步操作**: 数据库连接、CRUD、服务层、API层全部使用async/await
✅ **SQL Server支持**: 配置支持SQL Server异步连接
✅ **安全机制**: JWT认证、密码加密
✅ **完整测试**: Pytest异步测试框架
✅ **数据库迁移**: Alembic异步迁移配置
✅ **代码规范**: 使用Pydantic V2, SQLAlchemy 2.0

---

## 执行选项

**Plan complete and saved to `docs/plans/2025-03-22-enterprise-fastapi-setup.md`. Two execution options:**

**1. Subagent-Driven (this session)**
- I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)**
- Open new session with executing-plans, batch execution with checkpoints

**Which approach would you like to use?**
