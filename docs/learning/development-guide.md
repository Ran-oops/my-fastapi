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

| 工具   | 版本要求 | 用途       |
| ------ | -------- | ---------- |
| Python | 3.13+    | 运行环境   |
| UV     | 最新版   | 包管理     |
| just   | 最新版   | 命令运行器 |
| Git    | 2.x      | 版本控制   |
| Docker | 24+      | 数据库服务 |

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
just db-upgrade

# 6. 启动开发服务器
just run

# 7. 运行测试验证
just test
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
from app.modules.shared.db import CRUDBase
from app.modules.users.models import User

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

| 类型      | 命名规范            | 示例              |
| --------- | ------------------- | ----------------- |
| 模块      | snake_case          | `user_service.py` |
| 类        | PascalCase          | `UserService`     |
| 函数/方法 | snake_case          | `get_user_by_id`  |
| 常量      | UPPER_SNAKE_CASE    | `MAX_RETRY_COUNT` |
| 变量      | snake_case          | `user_count`      |
| 私有变量  | _leading_underscore | `_cache`          |

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
from app.modules.shared.db import CRUDBase
from app.modules.users.models import User
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

### 添加新领域模块

在 `app/modules/` 下创建新模块目录：

```text
app/modules/
├── users/                  # 用户领域
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy 模型
│   ├── schemas.py         # Pydantic schemas
│   ├── repository.py      # 数据访问层
│   ├── service.py         # 业务逻辑层
│   └── router.py          # API 路由
├── roles/                  # 角色权限领域
│   └── ...
└── orders/                 # 新模块示例
    ├── __init__.py
    ├── models.py
    ├── schemas.py
    ├── repository.py
    ├── service.py
    └── router.py
```

### Model 定义规范

```python
# app/modules/users/models.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.shared.db import UserDBBase


class User(UserDBBase):
    """用户模型."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
```

### Schema 定义规范

```python
# app/modules/users/schemas.py
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)
```

### Repository 定义规范

```python
# app/modules/users/repository.py
from app.modules.shared.db import CRUDBase
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate


class UserRepository(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


user_repository = UserRepository(User)
```

### Service 定义规范

```python
# app/modules/users/service.py
from app.core.exceptions import ConflictException
from app.modules.users.repository import user_repository
from app.modules.users.schemas import UserCreate


class UserService:
    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
        existing = await user_repository.get_by_email(db, email=user_in.email)
        if existing:
            raise ConflictException(f"Email {user_in.email} already registered")
        return await user_repository.create(db, obj_in=user_in)


user_service = UserService()
```

### Router 定义规范

```python
# app/modules/users/router.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_user_db as get_db
from app.modules.users.schemas import UserCreate, UserResponse
from app.modules.users.service import user_service

router = APIRouter()


@router.post("/", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    return await user_service.create_user(db, user_in)
```

### 注册路由

在 `app/api/v1/__init__.py` 中注册新模块的路由：

```python
from fastapi import APIRouter

from app.modules.users.router import router as users_router
from app.modules.roles.router import router as roles_router
from app.modules.orders.router import router as orders_router  # 新模块

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(roles_router, prefix="/roles", tags=["roles"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])  # 新模块
```

---

## 开发工作流

### 分支策略

```text
main (生产)
  │
  ├── develop (开发)
  │     │
  │     ├── feature/xxx (功能分支)
  │     ├── bugfix/xxx (修复分支)
  │     └── refactor/xxx (重构分支)
```

### 提交规范

使用 Conventional Commits：

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**类型**:

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

**示例**:

```bash
git commit -m "feat(users): add user registration endpoint"
git commit -m "fix(auth): handle expired tokens correctly"
git commit -m "docs: update API documentation"
```

---

## 测试指南

### 测试结构

```text
tests/
├── test_api/           # API 端点测试
│   ├── test_users.py
│   └── test_roles.py
├── test_services/      # Service 层测试
│   ├── test_user_service.py
│   └── test_role_service.py
└── conftest.py         # 测试 fixtures
```

### 运行测试

```bash
# 运行所有测试
just test

# 运行特定测试文件
uv run pytest tests/test_api/test_users.py -v

# 运行带有覆盖率
just test-cov
```

### 编写测试

```python
# tests/test_services/test_user_service.py
import pytest

from app.modules.users.schemas import UserCreate
from app.modules.users.service import user_service


@pytest.mark.asyncio
class TestUserService:
    async def test_create_user_success(self, db_session):
        user_in = UserCreate(
            email="test@example.com",
            username="testuser",
            password="testpassword123"
        )
        user = await user_service.create_user(db_session, user_in)
        assert user.email == "test@example.com"
        assert user.username == "testuser"
```

---

## 文档编写

### 文档结构

```text
docs/
├── learning/           # 学习文档
│   ├── architecture.md
│   ├── development-guide.md
│   ├── api-reference.md
│   └── ...
└── plans/              # 计划文档
    └── ...
```

### 更新文档

当代码结构发生变化时，需要更新以下文档：

1. `README.md` - 项目概览
2. `docs/learning/architecture.md` - 架构设计
3. `docs/learning/development-guide.md` - 开发指南

---

## 常见问题

### Q: 如何调试？

使用 VS Code 的调试配置：

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["app.main:app", "--reload"],
            "jinja": true
        }
    ]
}
```

### Q: 如何处理数据库迁移？

```bash
# 创建迁移
just db-migrate "描述变更"

# 应用迁移
just db-upgrade

# 回滚迁移
just db-downgrade
```

---

## 贡献指南

### 提交 PR 前

1. 确保所有测试通过：`just test`
2. 确保代码风格检查通过：`just lint`
3. 更新相关文档
4. 编写清晰的 PR 描述

### Code Review

- 所有 PR 需要至少 1 人审核
- 关键变更需要 2 人审核
- 审核关注点：
    - 代码质量
    - 测试覆盖
    - 文档完整性
    - 安全性

---

> 文档版本: 2.0.0
> 更新时间: 2026-03-25
