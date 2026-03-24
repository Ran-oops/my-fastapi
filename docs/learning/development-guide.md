# 开发指南

> 本文档提供 Enterprise FastAPI 项目的开发规范、贡献指南和常见问题解答。

## 目录

1. [开发环境设置](#开发环境设置)
2. [代码规范](#代码规范)
3. [项目结构约定](#项目结构约定)
4. [开发工作流](#开发工作流)
5. [测试指南](#测试指南)
6. [文档编写](#文档编写)
7. [常见问题](#常见问题)
8. [贡献指南](#贡献指南)

---

## 开发环境设置

### 前置要求

| 工具 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.13+ | 运行环境 |
| UV | 最新版 | 包管理 |
| Git | 2.x | 版本控制 |
| Docker | 24+ | 数据库服务 |

### 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/example/enterprise-fastapi.git
cd enterprise-fastapi

# 2. 安装依赖
uv sync --dev

# 3. 配置环境变量
cp .env.example .env

# 4. 启动数据库 (使用 Docker)
docker-compose up -d postgres mssql mysql

# 5. 运行数据库迁移
alembic upgrade head

# 6. 启动开发服务器
make run

# 7. 运行测试验证
make test
```

### 开发工具配置

#### VS Code 配置

创建 `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.linting.enabled": true,
    "python.formatting.provider": "none",
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        }
    },
    "ruff.lint.args": ["--config=ruff.toml"],
    "editor.rulers": [120]
}
```

---

## 代码规范

### Python 代码风格

遵循 PEP 8，使用 Ruff 进行检查和格式化：

```python
# ✅ 正确示例
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.base import CRUDBase

ModelType = TypeVar("ModelType")


class UserService:
    """用户服务类 - 处理用户相关业务逻辑."""
    
    @staticmethod
    async def get_user(db: AsyncSession, user_id: int) -> User | None:
        """获取单个用户.
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            用户对象或None
        """
        return await user_crud.get(db, id=user_id)


user_service = UserService()
```

### 命名规范

| 类型 | 命名规范 | 示例 |
|------|----------|------|
| 模块 | snake_case | `user_service.py` |
| 类 | PascalCase | `UserService` |
| 函数/方法 | snake_case | `get_user_by_id` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 变量 | snake_case | `user_count` |
| 私有变量 | _leading_underscore | `_cache` |

### Import 顺序

```python
# 1. 标准库
from datetime import datetime
from typing import TypeVar

# 2. 第三方库
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# 3. 本地应用
from app.core.config import settings
from app.crud.base import CRUDBase
from app.models.user import User
```

### 异步函数

```python
# ✅ 使用 async/await
async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())

# ❌ 避免同步阻塞
async def bad_example():
    time.sleep(1)  # 阻塞事件循环！
```

---

## 项目结构约定

### 添加新功能模块

创建一个新的业务模块需要以下文件：

```
app/
├── api/v1/endpoints/
│   └── new_module.py          # API 端点
├── crud/
│   └── new_module.py          # CRUD 操作
├── models/
│   ├── user_db/
│   │   └── new_module.py      # 用户库模型
│   └── business_db/
│       └── new_module.py      # 业务库模型
├── schemas/
│   └── new_module.py          # Pydantic 模型
└── services/
    └── new_module.py          # 业务逻辑
```

### Model 定义规范

```python
# app/models/<database>/models.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import UserDBBase  # 或 BusinessDBBase


class NewModel(UserDBBase):
    """模型文档说明."""
    
    __tablename__ = "new_table"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # 关系定义
    # items: Mapped[list["Item"]] = relationship("Item", back_populates="new_model")
```

### Schema 定义规范

```python
# app/schemas/new_module.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class NewModelBase(BaseModel):
    """基础 Schema."""
    name: str
    description: str | None = None


class NewModelCreate(NewModelBase):
    """创建用 Schema."""
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v


class NewModelUpdate(BaseModel):
    """更新用 Schema - 所有字段可选."""
    name: str | None = None
    description: str | None = None


class NewModelResponse(NewModelBase):
    """响应 Schema."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
```

### Service 定义规范

```python
# app/services/new_module.py
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.crud.new_module import new_model_crud
from app.models.new_module import NewModel
from app.schemas.new_module import NewModelCreate, NewModelUpdate


class NewModelService:
    """新模块服务类."""
    
    @staticmethod
    async def get_by_id(db: AsyncSession, model_id: int) -> NewModel:
        """获取单个资源."""
        model = await new_model_crud.get(db, id=model_id)
        if not model:
            raise NotFoundException(f"Model {model_id} not found")
        return model
    
    @staticmethod
    async def create(db: AsyncSession, obj_in: NewModelCreate) -> NewModel:
        """创建资源."""
        return await new_model_crud.create(db, obj_in=obj_in)


new_model_service = NewModelService()
```

### API 端点定义规范

```python
# app/api/v1/endpoints/new_module.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_db
from app.schemas.new_module import NewModelCreate, NewModelResponse
from app.services.new_module import new_model_service

router = APIRouter()


@router.get("/{model_id}", response_model=NewModelResponse)
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_user_db),
    _current_user = Depends(get_current_user),
):
    """获取单个资源."""
    return await new_model_service.get_by_id(db, model_id)


@router.post("/", response_model=NewModelResponse, status_code=201)
async def create_model(
    obj_in: NewModelCreate,
    db: AsyncSession = Depends(get_user_db),
    _current_user = Depends(get_current_user),
):
    """创建资源."""
    return await new_model_service.create(db, obj_in)
```

### 注册路由

```python
# app/api/v1/__init__.py
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, new_module

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(new_module.router, prefix="/new-module", tags=["new-module"])
```

---

## 开发工作流

### Git 分支规范

```
main          # 生产分支
├── develop   # 开发分支
    ├── feature/xxx    # 功能分支
    ├── fix/xxx        # 修复分支
    └── refactor/xxx   # 重构分支
```

### 提交规范

```
<type>(<scope>): <subject>

类型 (type):
- feat: 新功能
- fix: 修复 bug
- docs: 文档更新
- style: 代码格式 (不影响功能)
- refactor: 重构
- test: 测试相关
- chore: 构建/工具相关

示例:
feat(user): add user profile API
fix(auth): resolve token expiration issue
docs(api): update API documentation
```

### 开发流程

```bash
# 1. 从 develop 创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/add-user-profile

# 2. 开发功能
# ... 编写代码 ...

# 3. 运行测试和检查
make check

# 4. 提交代码
git add .
git commit -m "feat(user): add user profile API"

# 5. 推送到远程
git push origin feature/add-user-profile

# 6. 创建 Pull Request
# 在 GitHub 上创建 PR 到 develop 分支
```

---

## 测试指南

### 测试结构

```
tests/
├── __init__.py
├── conftest.py              # 共享 fixtures
├── test_api/                # API 测试
│   ├── __init__.py
│   ├── test_auth.py
│   └── test_users.py
└── test_services/           # 服务层测试
    ├── __init__.py
    └── test_user_service.py
```

### 编写测试

```python
# tests/conftest.py
import asyncio
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_user_db


TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话."""
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

```python
# tests/test_api/test_users.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    """测试获取当前用户."""
    # 先登录获取 token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "Test1234"
    })
    token = login_response.json()["data"]["access_token"]
    
    # 获取当前用户
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """测试用户注册."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "NewUser123"
    })
    
    assert response.status_code == 201
    assert response.json()["data"]["email"] == "newuser@example.com"
```

### 运行测试

```bash
# 运行所有测试
make test
# 或
uv run pytest tests -v

# 运行特定测试文件
uv run pytest tests/test_api/test_users.py -v

# 运行特定测试
uv run pytest tests/test_api/test_users.py::test_get_current_user -v

# 运行并生成覆盖率报告
uv run pytest tests -v --cov=app --cov-report=html
```

---

## 文档编写

### 代码文档

```python
async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> list[User]:
    """获取用户列表.
    
    Args:
        db: 数据库会话
        skip: 跳过数量
        limit: 返回数量限制
        
    Returns:
        用户列表
        
    Raises:
        UnauthorizedException: 未认证时抛出
        
    Example:
        >>> users = await get_users(db, skip=0, limit=10)
        >>> len(users)
        10
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())
```

### API 文档

使用 FastAPI 自动生成的 OpenAPI 文档：

```python
@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="获取指定用户",
    description="根据用户ID获取用户详细信息",
    responses={
        200: {"description": "成功获取用户"},
        404: {"description": "用户不存在"},
    }
)
async def get_user(user_id: int):
    ...
```

---

## 常见问题

### Q: 如何添加新的数据库表?

A:
1. 在 `app/models/<database>/` 创建模型文件
2. 在 `alembic/` 生成迁移脚本
3. 运行 `alembic upgrade head`

### Q: 如何添加新的 API 端点?

A:
1. 创建 Schema (`app/schemas/`)
2. 创建 Model (`app/models/`)
3. 创建 CRUD (`app/crud/`)
4. 创建 Service (`app/services/`)
5. 创建 Endpoint (`app/api/v1/endpoints/`)
6. 注册路由 (`app/api/v1/__init__.py`)

### Q: 为什么使用静态方法模式?

A: Service 层是纯业务逻辑，不依赖外部状态。使用静态方法模式：
- 简化调用，无需依赖注入
- 业务逻辑可复用（CLI 和 API 都可调用）
- 保持函数式风格

### Q: 如何处理跨数据库事务?

A: 目前不支持自动跨数据库事务。需要手动实现补偿机制：
```python
try:
    await db1.commit()
    await db2.commit()
except Exception:
    await db1.rollback()
    await db2.rollback()
    raise
```

### Q: 如何优化查询性能?

A:
1. 使用索引 (`index=True`)
2. 使用 `selectinload` 预加载关系
3. 分页查询
4. 避免 N+1 查询

---

## 贡献指南

### 提交 Issue

1. 搜索现有 Issue，避免重复
2. 选择合适的模板
3. 提供详细的描述和复现步骤
4. 添加相关标签

### 提交 PR

1. Fork 仓库
2. 创建功能分支
3. 编写测试
4. 保持代码规范
5. 更新文档
6. 提交 PR 并关联 Issue

### Code Review

- 至少需要一个批准
- 通过所有 CI 检查
- 解决所有 review comments

### 代码质量检查

```bash
# 运行所有检查
make check

# 单独运行
make lint      # 代码检查
make format    # 格式化代码
make test      # 运行测试
```

---

## 工具参考

### Makefile 命令

| 命令 | 说明 |
|------|------|
| `make run` | 启动开发服务器 |
| `make test` | 运行测试 |
| `make lint` | 运行代码检查 |
| `make format` | 格式化代码 |
| `make check` | 运行所有检查 |
| `make clean` | 清理缓存 |
| `make db-upgrade` | 运行数据库迁移 |

### UV 命令

| 命令 | 说明 |
|------|------|
| `uv sync` | 安装/更新依赖 |
| `uv add <pkg>` | 添加依赖 |
| `uv add --dev <pkg>` | 添加开发依赖 |
| `uv remove <pkg>` | 移除依赖 |
| `uv run <cmd>` | 在虚拟环境运行命令 |
| `uv lock` | 更新锁文件 |

### Ruff 命令

| 命令 | 说明 |
|------|------|
| `ruff check .` | 检查代码 |
| `ruff check --fix .` | 自动修复 |
| `ruff format .` | 格式化代码 |

---

> 文档版本: 1.0.0
> 更新时间: 2026-03-24