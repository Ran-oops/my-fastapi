# FastAPI dependency-injector 集成指南

## 概述

本项目已集成 `dependency-injector` 库，提供企业级依赖注入框架。本文档介绍如何使用 DI 容器来管理依赖。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                         FastAPI App                          │
├─────────────────────────────────────────────────────────────┤
│                     app/api/deps.py                          │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              DI Container (app/core/container.py)       │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │ │
│  │  │  Config     │  │ Database    │  │ Repositories    │  │ │
│  │  │  Providers  │  │ Providers   │  │ (Singleton)     │  │ │
│  │  │             │  │             │  │                 │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │ │
│  └───────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Routers (app/api/v1/*.py)                │
│              ↓ Use DI Container via FastAPI Depends         │
├─────────────────────────────────────────────────────────────┤
│                    Services (app/modules/*/service.py)      │
│              ↓ Call Repository methods                        │
├─────────────────────────────────────────────────────────────┤
│                    Repositories (app/modules/*/repository.py) │
│              ↓ Use Database Sessions                         │
├─────────────────────────────────────────────────────────────┤
│                    Database (SQLAlchemy Async)              │
└─────────────────────────────────────────────────────────────┘
```

## 核心概念

### 1. Container (app/core/container.py)

主容器定义所有应用依赖：

```python
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    # 配置
    config = providers.Configuration()

    # 数据库会话
    db_session = providers.Factory(get_session)

    # Repository (单例模式)
    user_repository = providers.Singleton(UserRepository, model=User)
    order_repository = providers.Singleton(OrderRepository, model=Order)

# 全局容器实例
container = Container()
```

### 2. Provider 类型

| Provider | 用途 | 生命周期 |
|----------|------|----------|
| `Singleton` | Repository、配置 | 全局唯一实例 |
| `Factory` | Service、临时对象 | 每次请求新实例 |
| `Resource` | 异步资源 (Redis等) | 初始化/清理管理 |
| `Configuration` | 环境配置 | 动态配置加载 |

### 3. 使用方式

#### 方式一：直接容器访问 (当前主要方式)

```python
from app.core.container import container
from app.api.deps import get_session

@router.get("/users")
async def list_users(session: AsyncSession = Depends(get_session)):
    # 从容器获取 repository
    user_repo = container.user_repository()
    users = await user_repo.get_multi(session, skip=0, limit=100)
    return users
```

#### 方式二：FastAPI 依赖注入

```python
from app.api.deps import get_current_user

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

#### 方式三：@inject 装饰器 (高级)

```python
from dependency_injector.wiring import Provide, inject
from app.core.container import Container

@router.get("/test")
@inject
async def test(
    user_repo: UserRepository = Depends(Provide[Container.user_repository]),
):
    # user_repo 会自动从容器注入
    pass
```

## 配置容器

### app/core/config.py

```python
class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # 缓存配置
    CACHE_ENABLED: bool = True

settings = Settings()
```

### app/core/container.py

```python
class Container(containers.DeclarativeContainer):
    # 从环境变量加载配置
    config = providers.Configuration()
    config.DATABASE_URL.from_env("DATABASE_URL", default="sqlite+aiosqlite:///./app.db")
    config.REDIS_URL.from_env("REDIS_URL", default="redis://localhost:6379/0")

    # 数据库引擎
    db_engine = providers.Singleton(
        create_async_engine,
        config.DATABASE_URL,
    )

    # Redis 客户端
    redis_client = providers.Resource(
        init_redis,
        url=config.REDIS_URL,
    )
```

## Repository 层 DI

### 当前方式 (单例模式)

```python
# app/modules/users/repository.py
class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        ...

# 单例实例
user_repo = UserRepository(User)

# 使用
from app.modules.users.repository import user_repo
user = await user_repo.get(session, id=user_id)
```

### 新方式 (DI 容器)

```python
# app/core/container.py
user_repository = providers.Singleton(UserRepository, model=User)

# 使用
from app.core.container import container
user_repo = container.user_repository()
user = await user_repo.get(session, id=user_id)
```

## Service 层 DI

### 当前方式 (函数式)

```python
# app/modules/users/service.py
async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await user_repo.get(session, id=user_id)
```

### 新方式 (类式 + DI)

```python
# app/modules/users/service.py
class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repo = user_repository

    async def get_by_id(self, session: AsyncSession, user_id: int) -> User | None:
        return await self.user_repo.get(session, id=user_id)

# Container
user_service = providers.Factory(UserService, repo=user_repository)

# 使用
user_service = container.user_service()
user = await user_service.get_by_id(session, user_id)
```

## Router 层 DI

### app/modules/users/user_router.py

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_session, get_current_user
from app.core.container import container

router = APIRouter()

@router.get("/users")
async def list_users(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """使用 FastAPI Depends 获取依赖"""
    user_repo = container.user_repository()
    users = await user_repo.get_multi(session, skip=0, limit=100)
    return users
```

## 测试中的 DI

### 替换 Repository 为 Mock

```python
# tests/conftest.py
import pytest
from app.core.container import container

@pytest.fixture
def mock_user_repo():
    class MockUserRepository:
        async def get(self, session, id):
            return User(id=id, email="test@example.com")

    return MockUserRepository()

@pytest.fixture(autouse=True)
def override_dependencies(mock_user_repo):
    """Override container dependencies for testing"""
    container.user_repository.override(mock_user_repo)
    yield
    container.user_repository.reset_override()
```

## 最佳实践

### 1. 使用 Singleton 管理 Repository

```python
# 正确：Repository 是无状态的，使用 Singleton
user_repository = providers.Singleton(UserRepository, model=User)

# 错误：Repository 不应该每次创建新实例
user_repository = providers.Factory(UserRepository, model=User)
```

### 2. 配置从环境变量加载

```python
# 正确
config.DATABASE_URL.from_env("DATABASE_URL", default="...")

# 错误 - 硬编码
config.DATABASE_URL = "sqlite:///..."
```

### 3. 服务函数保持纯函数

```python
# 正确：函数接受 session 作为参数
async def create_user(session: AsyncSession, data: UserCreate) -> User:
    return await user_repo.create(session, data)

# 错误：在函数内部创建 session
async def create_user(data: UserCreate) -> User:
    async with get_session() as session:  # ❌
        return await user_repo.create(session, data)
```

### 4. 依赖注入优先于全局导入

```python
# 推荐：使用 DI 获取依赖
@router.get("/users")
async def list_users(
    user_repo: UserRepository = Depends(Provide[Container.user_repository]),
):
    pass

# 避免：直接全局导入
from app.modules.users.repository import user_repo  # ❌
```

## 可用 Repository Providers

| Provider | 类型 | 描述 |
|----------|------|------|
| `container.user_repository` | Singleton | 用户数据访问 |
| `container.role_repository` | Singleton | 角色数据访问 |
| `container.permission_repository` | Singleton | 权限数据访问 |
| `container.order_repository` | Singleton | 订单数据访问 |
| `container.product_repository` | Singleton | 产品数据访问 |
| `container.audit_log_repository` | Singleton | 审计日志访问 |
| `container.config_repository` | Singleton | 系统配置访问 |
| `container.notification_repository` | Singleton | 通知数据访问 |
| `container.search_repository_factory` | Factory | 搜索仓库工厂 |

## 迁移指南

### 从旧模式迁移到 DI 模式

#### 步骤 1: 更新 Repository 定义

```python
# 旧：全局单例
user_repo = UserRepository(User)

# 新：容器管理
container.user_repository = providers.Singleton(UserRepository, model=User)
```

#### 步骤 2: 更新 Service 层

```python
# 旧：直接导入
from app.modules.users.repository import user_repo

# 新：从容器获取
from app.core.container import container
user_repo = container.user_repository()
```

#### 步骤 3: 更新 Router 层

```python
# 旧：直接调用 service
from app.modules.users import service as user_service

# 新：使用 DI (可选)
from app.core.container import container
user_repo = container.user_repository()
```

## 参考

- [dependency-injector 文档](https://python-dependency-injector.ets-labs.org/)
- [FastAPI 依赖注入](https://fastapi.tiangolo.com/tutorial/dependencies/)
