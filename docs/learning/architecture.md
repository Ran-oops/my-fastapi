# 架构设计文档

> 本文档描述 Enterprise FastAPI 项目的整体架构设计、设计模式和技术选型理由。

## 目录

1. [架构概览](#架构概览)
2. [领域驱动设计](#领域驱动设计)
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

本项目采用 **领域驱动设计 (Domain-Driven Design, DDD)** 结合 **依赖注入 (Dependency Injection)** 模式：

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
│  │   • 路由注册        • 依赖注入        • 中间件              │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        领域层 (Domain)                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    app/modules/                               │  │
│  │   • users/        • roles/          • shared/                │  │
│  │   • models        • schemas         • repository             │  │
│  │   • service       • router                                   │  │
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
| **单一职责** | 每个模块只负责一个领域 | users/, roles/ 独立模块 |
| **依赖倒置** | 高层不依赖低层，都依赖抽象 | 依赖注入、接口抽象 |
| **开闭原则** | 对扩展开放，对修改关闭 | 泛型CRUD基类、可配置中间件 |
| **接口隔离** | 客户端不应依赖不需要的接口 | 精细的Schema定义 |

---

## 领域驱动设计

### 模块结构

每个领域模块包含完整的垂直切片：

```
app/modules/users/
├── models.py      # SQLAlchemy 模型 (数据结构)
├── schemas.py     # Pydantic schemas (数据验证)
├── repository.py  # 数据访问层 (CRUD)
├── service.py     # 业务逻辑层
└── router.py      # API 路由 (接口)
```

### 依赖关系

```
router.py → service.py → repository.py → models.py
                ↓
            schemas.py
```

- **router.py**: 只依赖 service 和 schemas
- **service.py**: 只依赖 repository 和 schemas
- **repository.py**: 只依赖 models
- **schemas.py**: 不依赖任何领域代码

### 优势

1. **高内聚**: 相关代码在一个目录内
2. **低耦合**: 模块之间通过清晰接口交互
3. **易扩展**: 新增功能只需创建新模块目录
4. **易测试**: 每层可独立测试

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

```python
# app/modules/shared/db.py
user_engine = create_async_engine(settings.USER_DATABASE_URL, ...)
business_engine = create_async_engine(settings.BUSINESS_DATABASE_URL, ...)
config_engine = create_async_engine(settings.CONFIG_DATABASE_URL, ...)

UserSessionLocal = async_sessionmaker(user_engine, ...)
BusinessSessionLocal = async_sessionmaker(business_engine, ...)
ConfigSessionLocal = async_sessionmaker(config_engine, ...)
```

---

## 设计模式

### 1. 依赖注入模式 (Dependency Injection)

**实现位置**: `app/api/deps.py`

```python
async def get_user_db() -> AsyncSession:
    async with UserSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_user_db),
    current_user: User = Depends(get_current_user)
):
    ...
```

### 2. 单例模式 (Singleton)

```python
# app/modules/users/service.py
class UserService:
    ...

user_service = UserService()  # 模块级单例

# 使用方式
from app.modules.users.service import user_service
```

### 3. 模板方法模式 (Template Method)

**实现位置**: `app/modules/shared/db.py` - CRUDBase

```python
class CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]:
    async def get(self, db, id): ...
    async def create(self, db, obj_in): ...
    async def update(self, db, db_obj, obj_in): ...
    async def delete(self, db, id): ...

class UserRepository(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db, email): ...
    async def authenticate(self, db, username, password): ...
```

---

## 数据流设计

### API 请求处理流程

```
HTTP Request
    │
    ▼
FastAPI 路由匹配 (router.py)
    │
    ▼
Pydantic 验证 (schemas.py)
    │
    ▼
依赖注入 (deps.py)
    │
    ▼
Service 层处理 (service.py)
    │
    ▼
Repository 层处理 (repository.py)
    │
    ▼
数据库执行
    │
    ▼
响应返回
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

---

## 配置管理架构

### 配置层次

```
环境变量 (.env 文件)
    │
    ▼
Settings 类 (app/core/config.py)
    │
    ▼
settings 单例
```

---

## 依赖注入系统

### 依赖类型

```python
# 1. 数据库会话依赖
async def get_user_db() -> AsyncSession: ...

# 2. 认证依赖
async def get_current_user(...) -> User: ...
async def get_current_active_superuser(...) -> User: ...

# 3. 请求参数依赖
class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 10
```

---

## 扩展性设计

### 添加新领域模块

1. 在 `app/modules/` 创建新目录（如 `orders/`）
2. 创建以下文件：
   - `models.py` - SQLAlchemy 模型
   - `schemas.py` - Pydantic schemas
   - `repository.py` - 数据访问层
   - `service.py` - 业务逻辑层
   - `router.py` - API 路由
3. 在 `app/api/v1/__init__.py` 注册路由

### 添加新数据库

1. 在 `app/core/config.py` 添加数据库 URL
2. 在 `app/modules/shared/db.py` 创建引擎和会话
3. 配置 Alembic 迁移

---

> 文档版本: 2.0.0
> 更新时间: 2026-03-25
