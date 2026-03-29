# 快速参考卡片

> 本文档提供项目开发的快速参考，适合打印或书签使用。

## 目录

1. [API 端点速查](#api-端点速查)
2. [命令速查](#命令速查)
3. [代码模板](#代码模板)
4. [SQL 速查](#sql-速查)
5. [HTTP 状态码](#http-状态码)
6. [Pydantic 验证](#pydantic-验证)

---

## API 端点速查

### 认证接口

```text
POST   /api/v1/auth/register    # 注册
POST   /api/v1/auth/login       # 登录
```

### 用户接口

```text
GET    /api/v1/users/me         # 获取当前用户
GET    /api/v1/users/{id}       # 获取指定用户
GET    /api/v1/users/           # 用户列表 (管理员)
PUT    /api/v1/users/{id}       # 更新用户
DELETE /api/v1/users/{id}       # 删除用户 (管理员)
```

### 请求头

```bash
# 认证请求
Authorization: Bearer <token>

# 内容类型
Content-Type: application/json
```

### cURL 示例

```bash
# 注册
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"user","password":"Pass1234"}'

# 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"Pass1234"}'

# 获取当前用户
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <token>"
```

---

## 命令速查

### 开发命令

```bash
# 启动开发服务器
just run
# 或
uv run python run.py
# 或
uv run uvicorn app.main:app --reload

# 运行测试
just test
uv run pytest tests -v

# 代码检查
just lint
uv run ruff check app tests

# 格式化
just fmt
uv run ruff format app tests

# 类型检查
uv run ty check app

# 全部检查
just ruff
```

### 数据库命令

```bash
# 生成迁移
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看历史
alembic history

# 查看当前版本
alembic current
```

### UV 命令

```bash
# 安装依赖
uv sync
uv sync --dev

# 添加依赖
uv add package
uv add --dev package

# 移除依赖
uv remove package

# 更新锁文件
uv lock

# 运行命令
uv run python script.py
```

### Docker 命令

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down

# 重建启动
docker-compose up -d --build
```

---

## 代码模板

### 新 API 端点

```python
# app/api/v1/endpoints/new_module.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_db
from app.schemas.new_module import NewResponse, NewCreate
from app.services.new_module import new_service

router = APIRouter()


@router.get("/", response_model=list[NewResponse])
async def list_items(
    db: AsyncSession = Depends(get_user_db),
    _current_user = Depends(get_current_user),
):
    return await new_service.get_all(db)


@router.post("/", response_model=NewResponse, status_code=201)
async def create_item(
    obj_in: NewCreate,
    db: AsyncSession = Depends(get_user_db),
    _current_user = Depends(get_current_user),
):
    return await new_service.create(db, obj_in)
```

### 新 Service

```python
# app/modules/new_module/service.py
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.new_module.repository import new_repository
from app.modules.new_module.schemas import NewCreate


class NewService:
    @staticmethod
    async def get_all(db: AsyncSession):
        return await new_repository.get_multi(db)

    @staticmethod
    async def get_by_id(db: AsyncSession, item_id: int):
        item = await new_repository.get(db, id=item_id)
        if not item:
            raise NotFoundException(f"Item {item_id} not found")
        return item

    @staticmethod
    async def create(db: AsyncSession, obj_in: NewCreate):
        return await new_repository.create(db, obj_in=obj_in)


new_service = NewService()
```

### 新 Repository

```python
# app/modules/new_module/repository.py
from app.modules.shared.db import CRUDBase
from app.modules.new_module.models import NewModel
from app.modules.new_module.schemas import NewCreate, NewUpdate


class NewRepository(CRUDBase[NewModel, NewCreate, NewUpdate]):
    pass


new_repository = NewRepository(NewModel)
```

### 新 Model

```python
# app/modules/new_module/models.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.shared.db import UserDBBase


class NewModel(UserDBBase):
    __tablename__ = "new_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
```

### 新 Schema

```python
# app/modules/new_module/schemas.py
from pydantic import BaseModel


class NewBase(BaseModel):
    name: str


class NewCreate(NewBase):
    pass


class NewUpdate(BaseModel):
    name: str | None = None


class NewResponse(NewBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
```

---

## SQL 速查

### 查询

```sql
-- 基本查询
SELECT * FROM users WHERE is_active = true;

-- 条件查询
SELECT * FROM users 
WHERE email LIKE '%@example.com' 
  AND is_active = true;

-- OR 条件
SELECT * FROM users 
WHERE username = 'admin' 
   OR is_superuser = true;

-- IN 查询
SELECT * FROM users 
WHERE id IN (1, 2, 3);

-- 分页
SELECT * FROM users 
ORDER BY created_at DESC 
LIMIT 10 OFFSET 0;

-- 计数
SELECT COUNT(*) FROM users WHERE is_active = true;
```

### 聚合

```sql
-- 分组统计
SELECT status, COUNT(*), SUM(total_amount)
FROM orders
GROUP BY status;

-- 最大/最小/平均
SELECT 
    MAX(price) as max_price,
    MIN(price) as min_price,
    AVG(price) as avg_price
FROM products;
```

### 连接

```sql
-- INNER JOIN
SELECT u.*, r.name as role_name
FROM users u
INNER JOIN user_roles ur ON u.id = ur.user_id
INNER JOIN roles r ON ur.role_id = r.id;

-- LEFT JOIN
SELECT u.*, r.name as role_name
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id;
```

---

## HTTP 状态码

### 成功 (2xx)

| 状态码 | 名称       | 使用场景       |
| ------ | ---------- | -------------- |
| 200    | OK         | GET 请求成功   |
| 201    | Created    | POST 创建成功  |
| 202    | Accepted   | 请求已接受处理 |
| 204    | No Content | DELETE 成功    |

### 客户端错误 (4xx)

| 状态码 | 名称                 | 使用场景      |
| ------ | -------------------- | ------------- |
| 400    | Bad Request          | 请求格式错误  |
| 401    | Unauthorized         | 未认证        |
| 403    | Forbidden            | 无权限        |
| 404    | Not Found            | 资源不存在    |
| 409    | Conflict             | 资源冲突/重复 |
| 422    | Unprocessable Entity | 验证失败      |
| 429    | Too Many Requests    | 请求过多      |

### 服务端错误 (5xx)

| 状态码 | 名称                  | 使用场景   |
| ------ | --------------------- | ---------- |
| 500    | Internal Server Error | 服务器错误 |
| 502    | Bad Gateway           | 网关错误   |
| 503    | Service Unavailable   | 服务不可用 |

---

## Pydantic 验证

### 类型验证

```python
from pydantic import BaseModel, EmailStr, Field, field_validator

class UserSchema(BaseModel):
    # 基本类型
    name: str
    age: int
    score: float
    is_active: bool

    # 可选
    email: str | None = None

    # 字符串格式
    email: EmailStr  # 自动验证邮箱格式

    # 数值范围
    age: int = Field(ge=0, le=150)
    score: float = Field(gt=0, le=100)

    # 字符串长度
    name: str = Field(min_length=1, max_length=100)

    # 默认值
    status: str = "active"
    tags: list[str] = []
```

### 自定义验证

```python
from pydantic import field_validator
import re

class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username too short")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Invalid characters")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password too short")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Need at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Need at least one digit")
        return v
```

---

## 常用导入

### FastAPI

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
```

### SQLAlchemy

```python
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload
```

### Pydantic

```python
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from pydantic import field_validator, model_validator
```

### 项目内部

```python
# 核心
from app.core.config import settings
from app.core.exceptions import *
from app.core.security import *

# 数据库
from app.db.session import get_user_db, get_business_db

# CRUD
from app.crud.user import user as user_crud

# 模型
from app.models.user import User

# Schema
from app.schemas.user import UserCreate, UserResponse

# Service
from app.services.user import user_service
```

---

## 错误处理速查

```python
# 抛出异常
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
)

# 使用
if not item:
    raise NotFoundException("Item not found")

if existing:
    raise ConflictException("Already exists")
```

---

## 日志速查

```python
import logging

# 获取 logger
logger = logging.getLogger(__name__)

# 记录日志
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")

# 带上下文
logger.info(f"User {user_id} logged in")
logger.error(f"Failed to process order: {exc}", exc_info=True)
```

---

## 环境变量速查

```bash
# 必需
SECRET_KEY=your-secret-key
USER_DATABASE_URL=postgresql+asyncpg://...
BUSINESS_DATABASE_URL=mssql+aioodbc://...
CONFIG_DATABASE_URL=mysql+aiomysql://...

# 可选
APP_ENV=development
DEBUG=True
API_V1_STR=/api/v1
ACCESS_TOKEN_EXPIRE_MINUTES=30
BACKEND_CORS_ORIGINS=*
LOG_LEVEL=INFO
```

---

> 文档版本: 1.0.0
> 更新时间: 2026-03-24
