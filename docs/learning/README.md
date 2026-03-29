# Enterprise FastAPI 项目学习指南

> 本文档为新手入门教程，帮助开发者全面了解本项目的架构、设计模式和技术实现。

## 文档导航

### 核心文档

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目概览和快速入门 (本页) |
| [architecture.md](architecture.md) | 架构设计文档 - 系统架构、设计模式、数据流 |
| [api-reference.md](api-reference.md) | API 接口文档 - 所有 RESTful API 详细说明 |
| [database.md](database.md) | 数据库设计文档 - 表结构、关系图、迁移管理 |
| [security.md](security.md) | 安全设计文档 - 认证授权、加密、安全最佳实践 |
| [deployment.md](deployment.md) | 部署运维文档 - 环境配置、部署流程、监控 |
| [development-guide.md](development-guide.md) | 开发指南 - 代码规范、贡献指南、常见问题 |

### 辅助文档

| 文档 | 说明 |
|------|------|
| [diagrams.md](diagrams.md) | 架构图与流程图 - 系统架构图、时序图、类图 |
| [examples.md](examples.md) | 代码示例 - API、Service、CRUD、测试代码模板 |
| [faq.md](faq.md) | FAQ 常见问题 - 开发中常见问题解答 |
| [glossary.md](glossary.md) | 术语表 - 项目专业术语解释 |
| [cheat-sheet.md](cheat-sheet.md) | 快速参考卡片 - API/命令/代码速查表 |
| [troubleshooting.md](troubleshooting.md) | 故障排查指南 - 常见错误诊断和解决方案 |

---

## 目录

1. [项目概述](#项目概述)
2. [技术栈分析](#技术栈分析)
3. [项目结构详解](#项目结构详解)
4. [多数据库架构](#多数据库架构)
5. [分层架构设计](#分层架构设计)
6. [核心模块详解](#核心模块详解)
7. [认证与授权](#认证与授权)
8. [CLI命令系统](#cli命令系统)
9. [最佳实践指南](#最佳实践指南)

---

## 项目概述

### 项目定位

这是一个**企业级FastAPI项目模板**，采用现代Python异步编程范式，支持多数据库架构和分层设计。项目体现了以下核心理念：

- **异步优先**：全面采用 async/await，提升并发处理能力
- **多数据库支持**：同时支持 PostgreSQL、SQL Server、MySQL
- **分层架构**：清晰分离 API、Service、CRUD、Model 层
- **类型安全**：使用 Pydantic V2 和 Python 3.13+ 类型注解
- **CLI 工具**：集成 Typer 构建命令行管理工具

### 核心特性

| 特性 | 说明 |
|------|------|
| RESTful API | 符合规范的 API 设计 |
| JWT 认证 | 支持 Access Token 和 Refresh Token |
| 多数据库 | 3 个独立数据库，支持读写分离 |
| 数据库迁移 | Alembic 多数据库迁移支持 |
| 自动化测试 | pytest + pytest-asyncio |
| 代码质量 | Ruff lint + Ty 类型检查 |

---

## 技术栈分析

### 核心框架

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Framework                       │
│                    (异步 Web 框架)                           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  SQLAlchemy   │    │  Pydantic V2  │    │   Alembic     │
│    2.0        │    │               │    │               │
│  ORM 异步支持  │    │  数据验证/序列化 │    │  数据库迁移   │
└───────────────┘    └───────────────┘    └───────────────┘
```

### 数据库驱动

| 数据库 | 驱动 | 用途 |
|--------|------|------|
| PostgreSQL | asyncpg | 用户认证、角色、权限 |
| SQL Server | aioodbc | 订单、产品、业务数据 |
| MySQL | aiomysql | 系统配置、字典数据(只读) |

### 开发工具

```
项目工具链:
├── uv          - 极速包管理器 (替代 pip)
├── ruff        - 代码检查和格式化 (替代 black+flake8)
├── ty          - 类型检查 (替代 mypy)
├── pytest      - 测试框架
└── pre-commit  - Git hooks 自动化
```

---

## 项目结构详解

```
mock_beige_fastapi_project/
├── app/                          # 主应用目录
│   ├── api/                      # API 路由层 (最外层)
│   │   ├── deps.py               # 依赖注入
│   │   └── v1/
│   │       ├── endpoints/        # 具体端点实现
│   │       │   ├── auth.py       # 认证端点
│   │       │   └── users.py      # 用户管理端点
│   │       └── __init__.py      # 路由汇总注册
│   │
│   ├── services/                 # 业务逻辑层 (核心层)
│   │   ├── user.py              # 用户服务
│   │   ├── fte.py               # FTE计算服务
│   │   ├── data_import.py       # 数据导入服务
│   │   └── qc_report.py         # 报表服务
│   │
│   ├── crud/                     # 数据访问层
│   │   ├── base.py              # CRUD 基础类
│   │   └── user.py              # 用户 CRUD
│   │
│   ├── models/                   # 数据模型层 (最底层)
│   │   ├── user_db/             # 用户数据库模型
│   │   ├── business_db/         # 业务数据库模型
│   │   └── config_db/           # 配置数据库模型
│   │
│   ├── schemas/                  # Pydantic 模型
│   │   ├── user.py             # 用户相关 schemas
│   │   └── common.py           # 通用响应模型
│   │
│   ├── core/                     # 核心配置模块
│   │   ├── config.py           # 全局配置
│   │   ├── security.py         # 安全工具 (JWT, 密码)
│   │   ├── exceptions.py       # 自定义异常
│   │   └── commands/           # 命令编排器
│   │
│   ├── db/                      # 数据库配置
│   │   ├── base.py             # 数据库基类
│   │   └── session.py          # 数据库会话管理
│   │
│   ├── cli/                     # 命令行工具
│   │   ├── __init__.py        # CLI 入口
│   │   └── commands/          # CLI 命令实现
│   │
│   └── main.py                 # FastAPI 应用入口
│
├── tests/                       # 测试目录
├── alembic/                     # 数据库迁移
├── manage.py                    # CLI 入口脚本
├── run.py                       # 应用启动脚本
└── pyproject.toml              # 项目配置
```

### 分层架构数据流

```
请求 → API Endpoint → Service → CRUD → Model → Database
                 ↓           ↓        ↓       ↓
响应 ← Schema验证    异常处理   会话管理  数据库连接
```

---

## 多数据库架构

### 设计理念

项目支持 **三个独立数据库**，每个数据库有明确的职责和访问模式：

```
┌──────────────────────────────────────────────────────────────────┐
│                         应用层 (FastAPI)                         │
└──────────────────────────────────────────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   User Database │   │ Business Database│   │ Config Database │
│   (PostgreSQL)  │   │   (SQL Server)   │   │    (MySQL)      │
│                 │   │                  │   │                 │
│ • 用户认证      │   │ • 订单管理       │   │ • 系统配置      │
│ • 角色权限      │   │ • 产品管理       │   │ • 字典数据      │
│ • 会话管理      │   │ • 业务统计       │   │ • 只读访问      │
└─────────────────┘   └─────────────────┘   └─────────────────┘
       Read/Write              Read/Write              Read Only
```

### 数据库会话管理

位置: `app/modules/shared/db.py`

```python
# 三个独立的数据库引擎和会话工厂

# User Database (PostgreSQL) - 读写
user_engine = create_async_engine(settings.USER_DATABASE_URL, ...)
UserSessionLocal = async_sessionmaker(...)

# Business Database (SQL Server) - 读写
business_engine = create_async_engine(settings.BUSINESS_DATABASE_URL, ...)
BusinessSessionLocal = async_sessionmaker(...)

# Config Database (MySQL) - 只读
config_engine = create_async_engine(settings.CONFIG_DATABASE_URL, ...)
ConfigSessionLocal = async_sessionmaker(...)
```

### 访问不同数据库

```python
# 在 API 端点中通过依赖注入选择数据库
from app.modules.shared.db import get_user_db, get_business_db, get_config_db

async def get_users(db: AsyncSession = Depends(get_user_db)):
    """使用用户数据库"""
    ...

async def get_orders(db: AsyncSession = Depends(get_business_db)):
    """使用业务数据库"""
    ...

async def get_config(db: AsyncSession = Depends(get_config_db)):
    """使用配置数据库"""
    ...
```

---

## 领域驱动设计架构

### 模块结构

每个领域模块包含完整的垂直切片：

```
app/modules/users/
├── models.py      # SQLAlchemy 模型
├── schemas.py     # Pydantic schemas
├── repository.py  # 数据访问层
├── service.py     # 业务逻辑层
└── router.py      # API 路由
```

### 依赖关系

```
router.py → service.py → repository.py → models.py
                ↓
            schemas.py
```

### 1. Router 层 (接口层)

**职责**: 处理 HTTP 请求/响应，路由分发，依赖注入

文件: `app/modules/users/router.py`

```python
@router.get("/", response_model=PaginatedResponse[UserResponse])
async def get_users(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_user_db),
    _current_user: User = Depends(get_current_active_superuser),
):
    users = await user_service.get_users(db, skip=pagination.skip, limit=pagination.limit)
    return PaginatedResponse(...)
```

### 2. Service 层 (业务层)

**职责**: 业务逻辑处理，事务协调，异常抛出

文件: `app/modules/users/service.py`

```python
class UserService:
    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
        # 业务逻辑：检查重复
        existing = await user_repository.get_by_email(db, email=user_in.email)
        if existing:
            raise ConflictException(f"Email {user_in.email} already registered")
        
        # 调用 Repository 层
        return await user_repository.create(db, obj_in=user_in)
```

### 3. Repository 层 (数据访问层)

**职责**: 数据库操作封装，通用查询方法

文件: `app/modules/users/repository.py`

```python
class UserRepository(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    async def authenticate(self, db: AsyncSession, username: str, password: str) -> User | None:
        # 密码验证
        user = await self.get_by_username(db, username=username)
        if not user:
            return None
        if not verify_password(password, str(user.hashed_password)):
            return None
        return user
```

### 4. Model 层 (数据模型层)

**职责**: 数据库表结构定义，关系映射

文件: `app/modules/users/models.py`

```python
class User(UserDBBase):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 关系定义
    roles: Mapped[list["Role"]] = relationship("Role", secondary="user_roles", ...)
```

### 5. Schema 层 (数据验证层)

**职责**: 数据验证，序列化，请求/响应模型

文件: `app/modules/users/schemas.py`

```python
class UserCreate(UserBase):
    email: EmailStr
    username: str
    password: str
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        # 密码强度验证
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        return v
```

### 6. 共享基础设施 (app/modules/shared/)

**职责**: 提供通用的数据库基类和响应模型

文件: `app/modules/shared/db.py`

```python
class CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]:
    async def get(self, db: AsyncSession, id: Any) -> ModelType | None: ...
    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> ModelType: ...
    async def update(self, db: AsyncSession, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType: ...
    async def delete(self, db: AsyncSession, id: int) -> ModelType | None: ...
```

文件: `app/modules/shared/schemas.py`

```python
class DataResponse[T](ResponseBase):
    data: T

class PaginatedResponse[T](ListResponse[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
```

---

## 核心模块详解

### 1. 配置管理 (app/core/config.py)

使用 Pydantic Settings 管理环境变量：

```python
class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    # 应用配置
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-this-secret-key-in-production"
    API_V1_STR: str = "/api/v1"
    
    # 数据库配置
    USER_DATABASE_URL: str = "postgresql+asyncpg://..."
    BUSINESS_DATABASE_URL: str = "mssql+aioodbc://..."
    CONFIG_DATABASE_URL: str = "mysql+aiomysql://..."
```

### 2. 安全模块 (app/core/security.py)

包含 JWT 和密码处理：

```python
# JWT Token 创建
def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

# 密码哈希
def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# 密码验证
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
```

### 3. 异常处理 (app/core/exceptions.py)

自定义异常类继承 HTTPException：

```python
class BaseAPIException(HTTPException):
    def __init__(self, status_code: int, detail: str, headers: dict | None = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class NotFoundException(BaseAPIException):
    """资源未找到 (404)"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ConflictException(BaseAPIException):
    """资源冲突 (409)"""
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
```

### 4. 依赖注入 (app/api/deps.py)

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_user_db), 
    token: str = Depends(oauth2_scheme)
) -> User:
    user_id = verify_token(token)
    if user_id is None:
        raise UnauthorizedException("Could not validate credentials")
    user = await user_repository.get(db, id=int(user_id))
    if user is None:
        raise UnauthorizedException("User not found")
    if user.is_active is False:
        raise UnauthorizedException("Inactive user")
    return user
```

### 5. 通用响应模型 (app/modules/shared/schemas.py)

```python
class DataResponse[T](ResponseBase):
    data: T
    # 格式: {"success": true, "message": "...", "data": {...}}

class PaginatedResponse[T](ListResponse[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
    # 支持分页的列表响应

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 10
    
    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size
```

---

## 认证与授权

### JWT 认证流程

```
1. 用户登录 (/api/v1/auth/login)
   │
   ▼
2. Service 验证用户名密码
   │
   ▼
3. 创建 JWT Token (包含 user_id)
   │
   ▼
4. 返回 Token 给客户端
   │
   ▼
5. 后续请求携带 Token (Authorization: Bearer <token>)
   │
   ▼
6. get_current_user 依赖验证 Token
   │
   ▼
7. 获取当前用户对象
```

### 密码安全

- 使用 bcrypt 进行密码哈希
- 密码长度限制 72 字节 (bcrypt 限制)
- 密码强度要求：至少 8 字符，包含字母和数字
- JWT 默认 30 分钟过期

### 权限控制

```python
# 普通用户 - 访问自己的资源
async def get_current_user(...) -> User:
    """获取当前登录用户"""
    
# 超级管理员 - 访问所有资源
async def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    """检查是否为超级管理员"""
    if current_user.is_superuser is False:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user
```

---

## CLI 命令系统

### CLI 架构

使用 Typer 构建命令行工具：

```
manage.py (入口)
    │
    ├── fte calculate          # FTE 计算命令
    ├── import-data            # 数据导入命令  
    └── qc-report              # QC 报告命令
```

### FTE 命令详解

文件: `app/cli/commands/fte.py`

```python
# 主命令：编排多个子命令顺序执行
@ app.command("calculate")
def calculate_fte(dry_run: bool = False, force: bool = False):
    steps = [
        ("Importing task listing", import_task_listing),
        ("Importing geographic SSU data", import_geographic_ssu_data),
        ("Calculating country FTE", calculate_country_fte),
        ("Calculating site FTE", calculate_site_fte),
        ("Calculating subregion FTE", calculate_subregion_fte),
        ("Generating final forecast", final_forecast),
    ]
    for step_name, step_func in steps:
        asyncio.run(step_func(dry_run=dry_run, force=force))

# 独立子命令
@app.command("import-task-listing")
def import_task_listing_cmd(dry_run: bool = False, force: bool = False):
    asyncio.run(import_task_listing(dry_run=dry_run, force=force))
```

### 运行 CLI 命令

```bash
# 运行完整 FTE 计算流程
python manage.py fte calculate --force

# 运行单个步骤
python manage.py fte import-task-listing --dry-run

# 查看帮助
python manage.py --help
python manage.py fte --help
```

---

## 最佳实践指南

### 1. 代码组织

```
新增功能时的文件放置:
├── 领域模块     → app/modules/<domain>/
│   ├── models.py      # 数据模型
│   ├── schemas.py     # 数据验证
│   ├── repository.py  # 数据库操作
│   ├── service.py     # 业务逻辑
│   └── router.py      # API 端点
├── CLI 命令     → app/cli/commands/
└── 共享代码     → app/modules/shared/
```

### 2. 错误处理

```python
# 在 Service 层抛出业务异常
class UserService:
    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
        existing = await user_repository.get_by_email(db, email=user_in.email)
        if existing:
            raise ConflictException("Email already registered")  # 业务异常
        return await user_repository.create(db, obj_in=user_in)
```

### 3. 数据库会话管理

```python
# 始终使用依赖注入获取数据库会话
async def get_user(db: AsyncSession = Depends(get_user_db)):
    ...

# 手动管理会话(仅在 CLI 或脚本中)
async with UserSessionLocal() as session:
    try:
        # 操作
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

### 4. 类型注解

```python
# 使用泛型定义通用类
class CRUDBase[ModelType, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel]:
    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        ...

# 使用 TypeVar 返回具体类型
async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    ...
```

### 5. 配置管理

```python
# 环境变量优先
# .env 文件 → Settings 类 → 默认值

# 开发环境配置
APP_ENV=development
DEBUG=True
SECRET_KEY=dev-secret-key

# 生产环境配置
APP_ENV=production
DEBUG=False
SECRET_KEY=<随机生成的安全密钥>
```

---

## 附录

### 常用命令

```bash
# 启动应用
just run
# 或
uv run python run.py

# 运行测试
just test

# 代码检查
just lint

# 格式化代码
just fmt

# 查看 API 文档
# http://localhost:8000/api/v1/docs
```

### 目录结构速查

| 目录 | 职责 |
|------|------|
| `app/modules/` | 业务领域模块 |
| `app/modules/users/` | 用户领域 (models, schemas, repository, service, router) |
| `app/modules/roles/` | 角色权限领域 |
| `app/modules/shared/` | 共享基础设施 (db, schemas) |
| `app/api/` | 路由注册、依赖注入 |
| `app/cli/` | 命令行工具 |
| `app/core/` | 核心配置 (config, security, exceptions) |

---

> 文档版本: 2.0.0
> 更新时间: 2026-03-25
> 项目地址: https://github.com/example/enterprise-fastapi