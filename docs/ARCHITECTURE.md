# Enterprise FastAPI - 完整架构文档

> **版本**: 2.0.0  
> **更新日期**: 2026-04-13  
> **状态**: 生产就绪

---

## 📋 目录

1. [项目概述](#项目概述)
2. [架构原则](#架构原则)
3. [技术栈](#技术栈)
4. [目录结构](#目录结构)
5. [核心架构](#核心架构)
6. [数据流](#数据流)
7. [安全设计](#安全设计)
8. [可观测性](#可观测性)
9. [性能优化](#性能优化)
10. [开发指南](#开发指南)

---

## 项目概述

这是一个**企业级 FastAPI 项目模板**，采用领域驱动设计（DDD）、异步全栈架构，集成了完整的可观测性和现代化的开发工具链。

### 核心特性

- ✅ **异步全栈** - Python 3.13 + FastAPI + SQLAlchemy 2.0
- ✅ **领域驱动设计** - 清晰的模块边界，Repository 模式
- ✅ **完整可观测性** - OpenTelemetry 追踪 + 结构化日志 + 指标
- ✅ **依赖注入** - 声明式 DI 容器
- ✅ **API 版本管理** - 语义化版本控制
- ✅ **限流与缓存** - Redis 限流 + 缓存层
- ✅ **后台任务** - Celery + Redis 任务队列

---

## 架构原则

### 1. 关注点分离

```
API Layer (Router)     → HTTP 协议、输入验证、序列化
Business Layer (Service) → 业务逻辑、事务管理
Data Layer (Repository)  → 数据访问、查询优化
Domain Layer (Model)     → 实体定义、业务规则
```

### 2. 依赖方向

```
Router → Service → Repository → Model
   ↓         ↓          ↓
   └─→ DI Container ←──┘
```

### 3. 异步优先

- 所有 I/O 操作使用 `async/await`
- 数据库会话使用 `AsyncSession`
- 任务队列使用异步执行

---

## 技术栈

### 核心框架

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | >=3.13 | 编程语言 |
| FastAPI | >=0.109.0 | Web 框架 |
| SQLAlchemy | >=2.0.0 | ORM |
| Pydantic | >=2.5.0 | 数据验证 |
| Pydantic Settings | >=2.1.0 | 配置管理 |

### 企业级组件

| 组件 | 版本 | 用途 |
|------|------|------|
| **structlog** | >=24.1.0 | 结构化日志 |
| **dependency-injector** | >=4.41.0 | 依赖注入 |
| **OpenTelemetry** | latest | 分布式追踪 |
| **slowapi** | latest | API 限流 |
| **aiocache** | >=0.12.0 | 异步缓存 |
| **Celery** | >=5.3.0 | 后台任务 |

### 数据库与缓存

| 组件 | 版本 | 用途 |
|------|------|------|
| asyncpg | >=0.29.0 | PostgreSQL 异步驱动 |
| aiosqlite | >=0.19.0 | SQLite 异步驱动 |
| Redis | >=5.0.0 | 缓存与消息队列 |
| Alembic | >=1.13.0 | 数据库迁移 |

### 安全与认证

| 组件 | 版本 | 用途 |
|------|------|------|
| python-jose | >=3.3.0 | JWT 处理 |
| bcrypt | >=4.0.0 | 密码哈希 |
| email-validator | >=2.1.0 | 邮箱验证 |

### 开发工具

| 工具 | 用途 |
|------|------|
| uv | 极速包管理 |
| just | 命令运行器 |
| ruff | Linter + Formatter |
| ty | 类型检查 |
| pytest | 测试框架 |

---

## 目录结构

```
project/
├── app/                          # 应用主目录
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口
│   ├── api/                      # API 层
│   │   ├── __init__.py
│   │   ├── deps.py               # FastAPI 依赖注入
│   │   ├── versioning.py         # API 版本管理
│   │   ├── v1/                   # v1 API 路由
│   │   │   └── __init__.py
│   │   └── v2/                   # v2 API 路由（预留）
│   │       └── __init__.py
│   ├── cli/                      # CLI 命令
│   │   ├── __init__.py
│   │   ├── commands/             # 命令实现
│   │   └── ...
│   ├── common/                   # 共享通用组件
│   │   ├── __init__.py
│   │   ├── pagination.py         # 分页模型
│   │   └── schemas.py            # 通用响应模型
│   ├── core/                     # 核心基础设施
│   │   ├── __init__.py
│   │   ├── cache.py              # 缓存配置
│   │   ├── config.py             # 应用配置
│   │   ├── container.py          # DI 容器
│   │   ├── events.py             # 事件定义
│   │   ├── eventbus.py           # 事件总线
│   │   ├── exceptions.py         # 自定义异常
│   │   ├── exception_handlers.py # 异常处理器
│   │   ├── logging.py            # 结构化日志
│   │   ├── middleware.py         # 中间件
│   │   ├── rate_limit.py         # 限流配置
│   │   ├── security.py           # 安全工具
│   │   └── telemetry.py          # OpenTelemetry
│   ├── db/                       # 数据库基础设施
│   │   ├── __init__.py
│   │   ├── base.py               # SQLAlchemy Base
│   │   ├── repository.py         # 基础 Repository
│   │   └── session.py            # 数据库会话
│   ├── modules/                  # 业务领域模块
│   │   ├── users/                # 用户模块
│   │   │   ├── __init__.py
│   │   │   ├── auth_router.py    # 认证路由
│   │   │   ├── associations.py   # 关联表
│   │   │   ├── models.py         # SQLAlchemy 模型
│   │   │   ├── repository.py     # 数据访问层
│   │   │   ├── schemas.py        # Pydantic schemas
│   │   │   ├── service.py        # 业务逻辑层
│   │   │   └── user_router.py    # 用户路由
│   │   ├── roles/                # 角色权限模块
│   │   ├── orders/               # 订单模块
│   │   ├── products/             # 产品模块
│   │   ├── audit/                # 审计模块
│   │   ├── config/               # 配置模块
│   │   ├── notifications/        # 通知模块
│   │   ├── search/               # 搜索模块
│   │   └── exports/              # 导出模块
│   └── tasks/                    # 后台任务（Celery）
│       ├── __init__.py
│       ├── beat_schedule.py      # 定时任务配置
│       ├── celery_app.py         # Celery 配置
│       ├── db.py                 # 同步数据库会话
│       ├── dispatcher.py         # 任务分发器
│       ├── models.py             # 任务模型
│       ├── repository.py         # 任务数据访问
│       ├── router.py             # 任务监控 API
│       ├── schemas.py            # 任务 schemas
│       ├── service.py            # 任务服务
│       └── signals.py            # Celery 信号
├── alembic/                      # 数据库迁移
├── docs/                         # 文档
│   ├── learning/                 # 学习文档
│   ├── superpowers/              # 设计文档
│   └── *.md                      # 架构文档
├── tests/                        # 测试
│   ├── conftest.py               # 全局 fixtures
│   ├── helpers.py                # 测试辅助
│   ├── core/                     # 核心测试
│   └── modules/                  # 模块测试
├── pyproject.toml                # 项目配置
├── README.md                     # 项目说明
└── justfile                      # 命令定义
```

---

## 核心架构

### 1. 依赖注入（DI）架构

```python
# app/core/container.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    """DI 容器 - 声明式依赖管理"""
    
    # 配置
    config = providers.Configuration()
    
    # 数据库会话工厂
    db_session = providers.Factory(get_session)
    
    # Repository - 单例模式
    user_repository = providers.Singleton(UserRepository, model=User)
    role_repository = providers.Singleton(RoleRepository, model=Role)
    
    # Service - 工厂模式
    user_service = providers.Factory(
        UserService,
        repo=user_repository,
        cache=cache_service,
    )
```

**使用方式**:

```python
# 方式 1: 自动注入
@router.get("/users/{user_id}")
@inject
async def get_user(
    user_id: int,
    user_service: UserService = Depends(Provide[Container.user_service]),
):
    return await user_service.get_by_id(user_id)

# 方式 2: 从容器获取
from app.core.container import Container
container = Container()
user_service = container.user_service()
```

### 2. Repository 模式

```python
# app/db/repository.py
class BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType]:
    """通用 Repository - 使用 Python 3.12+ 泛型语法"""
    
    def __init__(self, model: type[ModelType]):
        self.model = model
    
    async def get(self, session: AsyncSession, id: Any) -> ModelType | None:
        result = await session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, session: AsyncSession, data: CreateSchemaType) -> ModelType:
        instance = self.model(**data.model_dump())
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance
    
    async def create_multi(
        self, session: AsyncSession, data_list: list[CreateSchemaType]
    ) -> Sequence[ModelType]:
        """批量创建"""
        ...
    
    async def delete_multi(self, session: AsyncSession, ids: list[int]) -> int:
        """批量删除"""
        ...
```

### 3. 事件驱动架构

```python
# app/core/eventbus.py
@dataclass
class Event:
    event_type: str
    data: dict
    timestamp: datetime

class EventBus:
    """内存事件总线 - 轻量级发布/订阅"""
    
    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        ...
    
    def publish(self, event: Event):
        """发布事件"""
        ...

# 使用示例
@app.on_event("startup")
async def setup_event_handlers():
    eventbus.subscribe(ORDER_CONFIRMED, handle_order_notification)
    eventbus.subscribe(USER_REGISTERED, send_welcome_email)
```

### 4. 缓存架构

```python
# app/core/cache.py
from aiocache import cached, Cache
from aiocache.serializers import JsonSerializer

# 方式 1: 装饰器
cache = Cache(Cache.REDIS, endpoint="localhost", port=6379)

@cached(
    ttl=300,
    cache=Cache.REDIS,
    serializer=JsonSerializer(),
    key_builder=lambda f, *args, **kw: f"user:{kw['user_id']}"
)
async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await user_repo.get(session, id=user_id)

# 方式 2: 手动操作
async def update_user(session: AsyncSession, user_id: int, data: UserUpdate):
    user = await user_repo.update(session, user_id, data)
    await cache.delete(f"user:{user_id}")  # 失效缓存
    await cache.delete("users:list")        # 失效列表缓存
    return user
```

---

## 数据流

### 请求生命周期

```
HTTP Request
    ↓
[Rate Limiter] - slowapi
    ↓
[Auth Middleware] - JWT验证
    ↓
[OpenTelemetry Tracer] - 创建 span
    ↓
[Router] - FastAPI 路由匹配
    ↓
[DI Container] - 注入依赖
    ↓
[Service Layer] - 业务逻辑
    ↓
[Cache] - 检查缓存（可选）
    ↓
[Repository Layer] - 数据访问
    ↓
[Database] - SQLAlchemy 查询
    ↓
[Event Bus] - 发布事件（异步）
    ↓
[Celery Task] - 后台任务（可选）
    ↓
HTTP Response
```

### 日志与追踪关联

```python
# 每个请求自动包含
{
    "timestamp": "2024-01-01T12:00:00Z",
    "level": "info",
    "trace_id": "abc-123-xyz",
    "span_id": "def-456",
    "logger": "app.modules.users.service",
    "message": "User created successfully",
    "event": "user.created",
    "user_id": 123,
    "request_id": "req-789",
    "duration_ms": 45.2
}
```

---

## 安全设计

### 1. 认证流程

```
POST /auth/login
    ↓
验证用户名/密码 (bcrypt)
    ↓
生成 JWT (access_token + refresh_token)
    ↓
返回 Token

后续请求:
Authorization: Bearer {access_token}
    ↓
验证 JWT 签名
    ↓
检查用户存在且活跃
    ↓
注入当前用户到请求上下文
```

### 2. Token 策略

| Token 类型 | 有效期 | 用途 |
|-----------|--------|------|
| Access Token | 30分钟 | API 请求认证 |
| Refresh Token | 7天 | 刷新 Access Token |

### 3. 密码策略

- 最小长度：8 字符
- 必须包含：字母 + 数字
- 最大长度：72 字符（bcrypt 限制）
- 哈希算法：bcrypt
- 加密方式：单次哈希 + salt

### 4. API 限流

```python
# 全局默认限流
@router.post("/login")
@limiter.limit("10/minute")  # 登录接口限流
async def login(...):
    ...

# 按用户限流
@router.get("/users/me")
@limiter.limit("100/minute", per_user=True)
async def get_current_user(...):
    ...
```

---

## 可观测性

### 1. OpenTelemetry 追踪

```python
# 自动追踪的组件
- FastAPI HTTP 请求/响应
- SQLAlchemy 数据库查询
- Redis 操作
- Celery 任务

# 手动追踪示例
from app.core.telemetry import traced

@traced(span_name="process_order")
async def process_order(order_id: int, user_id: int):
    # 自动创建 span
    # span 属性: order_id, user_id
    ...

# 或使用上下文管理器
from app.core.telemetry import span_context

async def complex_operation():
    async with span_context("complex_operation") as span:
        span.set_attribute("step", "validation")
        await validate()
        
        span.set_attribute("step", "processing")
        await process()
```

### 2. 结构化日志

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# 基本日志
logger.info("User created", user_id=user.id, email=user.email)

# 带事件的日志
logger.info(
    "Order processed",
    event="order.processed",
    order_id=order.id,
    amount=order.total_amount,
    user_id=user.id,
)

# 错误日志
logger.error(
    "Payment failed",
    event="payment.failed",
    order_id=order.id,
    error_code="CARD_DECLINED",
    exc_info=True,
)
```

**输出示例（JSON 模式）**:

```json
{
  "timestamp": "2024-01-01T12:00:00.123Z",
  "level": "info",
  "logger": "app.modules.orders.service",
  "message": "Order processed",
  "event": "order.processed",
  "order_id": 123,
  "amount": 99.99,
  "user_id": 456,
  "trace_id": "abc-123-xyz",
  "span_id": "def-456",
  "service": "enterprise-fastapi",
  "version": "1.0.0"
}
```

### 3. 健康检查

```
GET /health         → 基础健康检查
GET /health/ready   → 就绪检查（包含数据库状态）
```

---

## 性能优化

### 1. 数据库优化

- **连接池**: SQLAlchemy 异步连接池
- **N+1 防护**: 使用 `selectinload` 预加载关系
- **批量操作**: `create_multi()`, `delete_multi()`
- **索引**: 所有外键和查询字段建立索引

### 2. 缓存策略

| 数据类型 | 缓存 TTL | 失效策略 |
|---------|---------|---------|
| 用户信息 | 5分钟 | 更新时失效 |
| 角色权限 | 10分钟 | 变更时失效 |
| 产品信息 | 30分钟 | 低频率更新 |
| 系统配置 | 60分钟 | 热更新支持 |

### 3. 异步优化

- 所有 I/O 操作使用 `async/await`
- 后台任务使用 Celery
- 事件处理使用异步 handler

### 4. 限流配置

```python
# 默认全局限流
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/minute"],
    storage_uri="redis://localhost:6379/1",
)
```

---

## 开发指南

### 1. 添加新模块

```bash
# 1. 创建目录结构
mkdir -p app/modules/<module_name>
touch app/modules/<module_name>/{__init__,models,schemas,repository,service,router}.py

# 2. 实现 Model
# app/modules/<module_name>/models.py
from app.db.base import UserBase

class <Module>(UserBase):
    __tablename__ = "<modules>"
    id: Mapped[int] = mapped_column(primary_key=True)
    # ...

# 3. 实现 Repository
# app/modules/<module_name>/repository.py
from app.db.repository import BaseRepository
from .models import <Module>
from .schemas import <Module>Create, <Module>Update

class <Module>Repository(BaseRepository[<Module>, <Module>Create, <Module>Update]):
    def __init__(self):
        super().__init__(<Module>)

<module>_repo = <Module>Repository()

# 4. 实现 Service
# app/modules/<module_name>/service.py
from .repository import <module>_repo

async def get_<module>_by_id(session: AsyncSession, id: int) -> <Module> | None:
    return await <module>_repo.get(session, id=id)

# 5. 实现 Router
# app/modules/<module_name>/router.py
from fastapi import APIRouter
from app.api.deps import get_session
from . import service

router = APIRouter()

@router.get("/{id}")
async def get_<module>(id: int, session=Depends(get_session)):
    return await service.get_<module>_by_id(session, id)

# 6. 注册路由
# app/api/v1/__init__.py
from app.modules.<module_name>.router import router as <module>_router
api_router.include_router(<module>_router, prefix="/<modules>", tags=["<modules>"])

# 7. 创建数据库迁移
alembic revision --autogenerate -m "add <module> table"
```

### 2. 使用 DI

```python
# 在 Service 中注入依赖
@inject
async def create_order(
    session: AsyncSession,
    data: OrderCreate,
    cache: CacheService = Provide[Container.cache_service],
    event_bus: EventBus = Provide[Container.event_bus],
):
    order = await order_repo.create(session, data)
    await cache.set(f"order:{order.id}", order)
    event_bus.publish(Event(ORDER_CREATED, {"order_id": order.id}))
    return order
```

### 3. 添加缓存

```python
# 方式 1: 装饰器
from app.core.cache import cached

@cached(ttl=300, key_builder=lambda f, *a, **kw: f"user:{kw['user_id']}")
async def get_user(user_id: int) -> User:
    ...

# 方式 2: 手动
from app.core.cache import cache

async def update_user(user_id: int, data: UserUpdate):
    await user_repo.update(user_id, data)
    await cache.delete(f"user:{user_id}")  # 失效缓存
```

### 4. 添加追踪

```python
from app.core.telemetry import traced, span_context

@traced(span_name="process_payment")
async def process_payment(order_id: int, amount: Decimal):
    # 自动追踪
    ...

# 或手动控制
async def complex_operation():
    with span_context("operation") as span:
        span.set_attribute("step", "1")
        await step1()
        span.set_attribute("step", "2")
        await step2()
```

### 5. 编写测试

```python
# tests/modules/<module>/test_<module>_service.py
import pytest
from app.modules.<module>.service import get_<module>_by_id

@pytest.mark.asyncio
async def test_get_<module>_by_id_found(session, test_<module>):
    result = await get_<module>_by_id(session, test_<module>.id)
    assert result is not None
    assert result.id == test_<module>.id

@pytest.mark.asyncio
async def test_get_<module>_by_id_not_found(session):
    result = await get_<module>_by_id(session, 99999)
    assert result is None
```

---

## 部署建议

### 生产环境配置

```env
# .env.production
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/app
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
SECRET_KEY=<random-32-char-key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080  # 7 days
RATE_LIMIT_DEFAULT=100/minute
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/app
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
  
  celery-worker:
    build: .
    command: celery -A app.tasks.celery_app worker -l info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
  
  celery-beat:
    build: .
    command: celery -A app.tasks.celery_app beat -l info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis

volumes:
  postgres_data:
  redis_data:
```

---

## 总结

本项目是一个**完整的企业级 FastAPI 模板**，具备：

- ✅ **现代化架构** - DDD + 异步 + DI
- ✅ **生产就绪** - 限流、缓存、任务队列
- ✅ **完整可观测性** - 追踪、日志、指标
- ✅ **安全第一** - JWT、bcrypt、限流
- ✅ **开发友好** - 类型安全、自动文档、测试覆盖

**技术先进性评级**: ⭐⭐⭐⭐⭐ (5/5)

---

## 参考文档

- [依赖注入指南](dependency_injection_guide.md)
- [缓存使用指南](cache.md)
- [API 版本策略](API_VERSIONING_STRATEGY.md)
- [迁移指南](migration/V1_TO_V2_GUIDE.md)
- [开发指南](learning/development-guide.md)

---

**作者**: Enterprise Team  
**许可证**: MIT
