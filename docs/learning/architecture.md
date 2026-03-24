# 架构设计文档

> 本文档描述 Enterprise FastAPI 项目的整体架构设计、设计模式和技术选型理由。

## 目录

1. [架构概览](#架构概览)
2. [分层架构](#分层架构)
3. [多数据库架构](#多数据库架构)
4. [设计模式](#设计模式)
5. [数据流设计](#数据流设计)
6. [错误处理架构](#错误处理架构)
7. [配置管理架构](#配置管理架构)
8. [依赖注入系统](#依赖注入系统)
9. [扩展性设计](#扩展性设计)

---

## 架构概览

### 架构风格

本项目采用 **分层架构 (Layered Architecture)** 结合 **依赖注入 (Dependency Injection)** 模式：

```
┌─────────────────────────────────────────────────────────────────────┐
│                         客户端 (Client)                              │
│                   Web / Mobile / Third-party                         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        表现层 (Presentation)                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                       API Layer (app/api/)                    │  │
│  │   • 路由定义        • 请求验证        • 响应序列化            │  │
│  │   • 依赖注入        • 中间件          • 认证授权              │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        业务层 (Business)                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Service Layer (app/services/)              │  │
│  │   • 业务逻辑        • 事务协调        • 异常处理              │  │
│  │   • 数据转换        • 验证规则        • 业务规则              │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        数据访问层 (Data Access)                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     CRUD Layer (app/crud/)                    │  │
│  │   • 数据查询        • 数据更新        • 会话管理              │  │
│  │   • 通用操作        • 自定义查询      • 连接池管理            │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        数据源层 (Data Source)                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  PostgreSQL     │  │   SQL Server    │  │     MySQL       │     │
│  │  (用户数据库)    │  │  (业务数据库)    │  │  (配置数据库)    │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### 核心设计原则

| 原则 | 描述 | 实现方式 |
|------|------|----------|
| **单一职责** | 每层只负责特定功能 | API层处理HTTP，Service层处理业务 |
| **依赖倒置** | 高层不依赖低层，都依赖抽象 | 依赖注入、接口抽象 |
| **开闭原则** | 对扩展开放，对修改关闭 | 泛型CRUD基类、可配置中间件 |
| **接口隔离** | 客户端不应依赖不需要的接口 | 精细的Schema定义 |

---

## 分层架构

### 1. API 层 (表现层)

**目录**: `app/api/`

**职责**:
- HTTP 请求/响应处理
- 路由定义和分发
- 请求参数验证
- 响应格式标准化
- 依赖注入入口

**组件结构**:

```
app/api/
├── __init__.py
├── deps.py                    # 依赖注入定义
└── v1/                        # API 版本 v1
    ├── __init__.py            # 路由汇总
    └── endpoints/             # 端点实现
        ├── auth.py            # 认证端点
        └── users.py           # 用户端点
```

**实现示例**:

```python
# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_db
from app.schemas.user import UserResponse, UserUpdate
from app.services.user import user_service

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息 - 依赖注入自动完成认证"""
    return current_user
```

### 2. Service 层 (业务层)

**目录**: `app/services/`

**职责**:
- 核心业务逻辑实现
- 跨表事务协调
- 业务规则验证
- 异常抛出和处理
- 数据转换和映射

**设计模式 - 静态方法模式**:

```python
# app/services/user.py
class UserService:
    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
        # 业务规则1: 检查邮箱唯一性
        existing = await user_crud.get_by_email(db, email=user_in.email)
        if existing:
            raise ConflictException(f"Email {user_in.email} already registered")
        
        # 业务规则2: 检查用户名唯一性
        existing = await user_crud.get_by_username(db, username=user_in.username)
        if existing:
            raise ConflictException(f"Username {user_in.username} already taken")
        
        # 委托给 CRUD 层执行
        return await user_crud.create(db, obj_in=user_in)

# 单例导出
user_service = UserService()
```

**为什么不使用依赖注入到 Service 层？**
- Service 层是纯业务逻辑，不依赖外部状态
- 静态方法模式简化调用，无需注入
- 业务逻辑可复用，可在 CLI 和 API 中使用

### 3. CRUD 层 (数据访问层)

**目录**: `app/crud/`

**职责**:
- 数据库 CRUD 操作封装
- 通用查询方法实现
- 会话管理
- 连接池交互

**泛型基类设计**:

```python
# app/crud/base.py
from typing import TypeVar, Generic

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        self.model = model
    
    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> Sequence[ModelType]:
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
```

**具体 CRUD 实现**:

```python
# app/crud/user.py
class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def authenticate(
        self, db: AsyncSession, username: str, password: str
    ) -> User | None:
        user = await self.get_by_username(db, username=username)
        if not user:
            return None
        if not verify_password(password, str(user.hashed_password)):
            return None
        return user

# 单例实例
user = CRUDUser(User)
```

### 4. Model 层 (数据模型层)

**目录**: `app/models/`

**职责**:
- 数据库表结构定义
- ORM 映射
- 关系定义
- 基础字段注入

**多数据库基类设计**:

```python
# app/db/base.py
from sqlalchemy.orm import declarative_base, declared_attr

class UserBase:
    """用户数据库基类 (PostgreSQL) - 包含时间戳"""
    @declared_attr
    def created_at(cls):
        return Column(DateTime, server_default=func.now())
    
    @declared_attr
    def updated_at(cls):
        return Column(DateTime, server_default=func.now(), onupdate=func.now())

class BusinessBase:
    """业务数据库基类 (SQL Server) - 包含时间戳"""
    # 同样包含 created_at, updated_at

class ConfigBase:
    """配置数据库基类 (MySQL - 只读) - 无时间戳"""
    pass

# 创建独立的 declarative_base
UserDBBase = declarative_base(cls=UserBase)
BusinessDBBase = declarative_base(cls=BusinessBase)
ConfigDBBase = declarative_base(cls=ConfigBase)
```

### 5. Schema 层 (数据验证层)

**目录**: `app/schemas/`

**职责**:
- 请求/响应数据模型定义
- 数据验证规则
- 数据转换和序列化

**Schema 分层设计**:

```python
# app/schemas/user.py

# 1. 基础 Schema - 公共字段
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None
    is_active: bool = True

# 2. 创建 Schema - 包含必需的创建字段
class UserCreate(UserBase):
    password: str
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        # 密码强度验证
        return v

# 3. 更新 Schema - 所有字段可选
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    password: str | None = None

# 4. 数据库 Schema - 包含数据库字段
class UserInDB(UserBase):
    id: int
    hashed_password: str
    is_superuser: bool
    model_config = ConfigDict(from_attributes=True)

# 5. 响应 Schema - 不包含敏感字段
class UserResponse(UserBase):
    id: int
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

---

## 多数据库架构

### 数据库分区策略

```
┌────────────────────────────────────────────────────────────────┐
│                        应用层 (FastAPI)                        │
└────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌─────────────────┬─────────────────┬─────────────────┐
    │  User Database  │Business Database│ Config Database │
    │   PostgreSQL    │   SQL Server    │     MySQL       │
    ├─────────────────┼─────────────────┼─────────────────┤
    │ • 用户表        │ • 订单表        │ • 配置表        │
    │ • 角色表        │ • 订单项表      │ • 字典表        │
    │ • 权限表        │ • 产品表        │ • 枚举表        │
    │ • 用户角色关联  │                 │                 │
    │ • 角色权限关联  │                 │                 │
    ├─────────────────┼─────────────────┼─────────────────┤
    │   Read/Write    │   Read/Write    │   Read Only     │
    └─────────────────┴─────────────────┴─────────────────┘
```

### 数据库独立性设计

每个数据库有独立的：
1. **连接引擎** (AsyncEngine)
2. **会话工厂** (async_sessionmaker)
3. **依赖注入函数** (get_xxx_db)
4. **基类** (declarative_base)
5. **Alembic 迁移配置**

```python
# 独立的连接配置
user_engine = create_async_engine(settings.USER_DATABASE_URL, ...)
business_engine = create_async_engine(settings.BUSINESS_DATABASE_URL, ...)
config_engine = create_async_engine(settings.CONFIG_DATABASE_URL, ...)

# 独立的会话工厂
UserSessionLocal = async_sessionmaker(user_engine, ...)
BusinessSessionLocal = async_sessionmaker(business_engine, ...)
ConfigSessionLocal = async_sessionmaker(config_engine, ...)
```

### 跨数据库事务处理

**问题**: 无法直接实现跨数据库的 ACID 事务

**解决方案**: 最终一致性模式

```python
# 伪代码示例
async def transfer_order_to_user_db(order_data, user_id):
    """创建订单时，需要同时更新业务库和用户库"""
    try:
        # 1. 在业务库创建订单
        order = await business_crud.create_order(db=business_db, data=order_data)
        
        # 2. 在用户库更新用户订单计数
        await user_crud.increment_order_count(db=user_db, user_id=user_id)
        
        # 3. 提交 (分别提交两个数据库)
        await business_db.commit()
        await user_db.commit()
        
    except Exception as e:
        # 手动回滚
        await business_db.rollback()
        await user_db.rollback()
        # 记录日志，可能需要补偿操作
        raise
```

---

## 设计模式

### 1. 依赖注入模式 (Dependency Injection)

**实现位置**: `app/api/deps.py`

```python
# 定义可注入的依赖
async def get_user_db() -> AsyncSession:
    async with UserSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# 在端点中使用
@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_user_db),  # 自动注入
    current_user: User = Depends(get_current_user)  # 认证依赖
):
    ...
```

**优点**:
- 松耦合
- 易于测试 (可 mock)
- 配置灵活

### 2. 单例模式 (Singleton)

**实现位置**: 每个模块末尾

```python
# app/crud/user.py
class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    ...

# 模块级单例
user = CRUDUser(User)

# app/services/user.py
class UserService:
    ...

# 模块级单例
user_service = UserService()
```

**使用方式**:
```python
# 导入单例实例，而非类
from app.crud.user import user as user_crud
from app.services.user import user_service
```

### 3. 模板方法模式 (Template Method)

**实现位置**: `app/crud/base.py`

```python
class CRUDBase:
    """定义通用操作模板"""
    async def get(self, db, id): ...
    async def create(self, db, obj_in): ...
    async def update(self, db, db_obj, obj_in): ...
    async def delete(self, db, id): ...

class CRUDUser(CRUDBase):
    """扩展特定方法"""
    async def get_by_email(self, db, email): ...
    async def authenticate(self, db, username, password): ...
```

### 4. 策略模式 (Strategy)

**实现位置**: 多数据库会话选择

```python
# 根据不同场景选择不同的数据库会话
async def get_current_db(
    db_type: str = "user"
) -> AsyncSession:
    if db_type == "user":
        async with UserSessionLocal() as session:
            yield session
    elif db_type == "business":
        async with BusinessSessionLocal() as session:
            yield session
    elif db_type == "config":
        async with ConfigSessionLocal() as session:
            yield session
```

---

## 数据流设计

### API 请求处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        HTTP Request                             │
│    POST /api/v1/users/register                                 │
│    Body: {"email": "user@example.com", "password": "..."}      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    1. FastAPI 路由匹配                           │
│    app.include_router(api_router, prefix="/api/v1")             │
│    api_router.include_router(users.router, prefix="/users")     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    2. Pydantic 验证                              │
│    UserCreate.validate(body) → 验证邮箱、密码强度                │
│    验证失败 → 422 Unprocessable Entity                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    3. 依赖注入                                   │
│    get_user_db() → 获取数据库会话                               │
│    (无认证要求，跳过 get_current_user)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    4. Service 层处理                             │
│    user_service.create_user(db, user_in)                        │
│    • 检查邮箱唯一性                                              │
│    • 检查用户名唯一性                                            │
│    • 调用 CRUD 创建用户                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    5. CRUD 层处理                                │
│    user_crud.create(db, obj_in)                                 │
│    • 密码哈希 (bcrypt)                                          │
│    • 构建 User 对象                                              │
│    • 执行 INSERT 语句                                            │
│    • 提交事务                                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    6. 数据库执行                                 │
│    INSERT INTO users (email, username, hashed_password, ...)    │
│    PostgreSQL 执行并返回结果                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    7. 响应返回                                   │
│    UserResponse.from_orm(user) → 序列化                          │
│    DataResponse[UserResponse](data=user, message="Created")     │
│    201 Created                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 异常处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    异常抛出点 (Service 层)                       │
│    raise ConflictException("Email already registered")          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BaseAPIException                             │
│    继承 HTTPException，包含 status_code 和 detail               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI 异常处理器                            │
│    自动转换为 HTTP 响应                                          │
│    409 Conflict: {"detail": "Email already registered"}         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 错误处理架构

### 异常层次结构

```
HTTPException (FastAPI)
    │
    └── BaseAPIException (app/core/exceptions.py)
            │
            ├── NotFoundException (404)
            ├── ConflictException (409)
            ├── UnauthorizedException (401)
            ├── ForbiddenException (403)
            └── ValidationException (422)
```

### 异常定义

```python
# app/core/exceptions.py
class BaseAPIException(HTTPException):
    def __init__(self, status_code: int, detail: str, headers: dict | None = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class NotFoundException(BaseAPIException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ConflictException(BaseAPIException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class UnauthorizedException(BaseAPIException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
```

### 错误响应格式

```json
{
    "detail": "Email user@example.com already registered",
    "status_code": 409,
    "error_type": "ConflictException"
}
```

---

## 配置管理架构

### 配置层次

```
┌─────────────────────────────────────────────────────────────────┐
│                    环境变量 (.env 文件)                          │
│    USER_DATABASE_URL=postgresql+asyncpg://...                   │
│    SECRET_KEY=your-secret-key                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Settings 类 (app/core/config.py)              │
│    继承 pydantic_settings.BaseSettings                          │
│    自动从环境变量加载                                            │
│    支持 .env 文件                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    settings 单例                                 │
│    settings = Settings()                                         │
│    全局可访问的配置对象                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 配置类实现

```python
# app/core/config.py
class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,  # 环境变量区分大小写
    )
    
    # 应用配置
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-secret-key-in-production"
    API_V1_STR: str = "/api/v1"
    
    # 数据库配置
    USER_DATABASE_URL: str
    BUSINESS_DATABASE_URL: str
    CONFIG_DATABASE_URL: str
    
    # 验证器
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> str | list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

# 全局单例
settings = Settings()
```

---

## 依赖注入系统

### 依赖类型

```python
# 1. 数据库会话依赖
async def get_user_db() -> AsyncSession: ...
async def get_business_db() -> AsyncSession: ...
async def get_config_db() -> AsyncSession: ...

# 2. 认证依赖
async def get_current_user(
    db: AsyncSession = Depends(get_user_db),
    token: str = Depends(oauth2_scheme)
) -> User: ...

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user)
) -> User: ...

# 3. 请求参数依赖
class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 10
```

### 依赖注入链

```
Endpoint
    │
    ├── Depends(get_user_db)        → 数据库会话
    │       │
    │       └── UserSessionLocal()  → SQLAlchemy 会话
    │
    ├── Depends(get_current_user)   → 当前用户
    │       │
    │       ├── Depends(get_user_db) → 数据库会话
    │       │
    │       └── Depends(oauth2_scheme) → Token
    │
    └── Depends(PaginationParams)   → 分页参数
```

---

## 扩展性设计

### 添加新数据库

1. 在 `app/core/config.py` 添加数据库 URL
2. 在 `app/db/session.py` 创建引擎和会话
3. 在 `app/db/base.py` 创建新的基类
4. 在 `app/models/` 创建模型目录
5. 配置 Alembic 迁移

### 添加新 API 模块

1. 在 `app/models/` 创建模型
2. 在 `app/schemas/` 创建 Schema
3. 在 `app/crud/` 创建 CRUD
4. 在 `app/services/` 创建 Service
5. 在 `app/api/v1/endpoints/` 创建端点
6. 在 `app/api/v1/__init__.py` 注册路由

### 添加新 CLI 命令

1. 在 `app/services/` 创建服务方法
2. 在 `app/cli/commands/` 创建命令文件
3. 在 `app/cli/__init__.py` 注册命令

---

> 文档版本: 1.0.0
> 更新时间: 2026-03-24