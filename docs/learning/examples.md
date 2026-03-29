# 代码示例

> 本文档提供项目开发中的常见代码示例和最佳实践。

## 目录

1. [API 端点示例](#api-端点示例)
2. [Service 层示例](#service-层示例)
3. [CRUD 操作示例](#crud-操作示例)
4. [数据库查询示例](#数据库查询示例)
5. [认证授权示例](#认证授权示例)
6. [错误处理示例](#错误处理示例)
7. [测试示例](#测试示例)
8. [CLI 命令示例](#cli-命令示例)

---

## API 端点示例

### 基本 GET 请求

```python
# app/api/v1/endpoints/items.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_db
from app.schemas.item import ItemResponse
from app.services.item import item_service

router = APIRouter()


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_user_db),
    _current_user = Depends(get_current_user),
):
    """获取单个资源."""
    return await item_service.get_by_id(db, item_id)
```

### 带分页的列表查询

```python
@router.get("/", response_model=PaginatedResponse[ItemResponse])
async def list_items(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_user_db),
    _current_user = Depends(get_current_user),
):
    """获取分页列表."""
    items = await item_service.get_items(
        db, 
        skip=pagination.skip, 
        limit=pagination.limit
    )
    total = await item_service.get_count(db)

    return PaginatedResponse(
        data=list(items),
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size,
    )
```

### 带查询参数的过滤

```python
from typing import Annotated
from fastapi import Query

@router.get("/search", response_model=list[ItemResponse])
async def search_items(
    keyword: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    category: Annotated[str | None, Query()] = None,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    db: AsyncSession = Depends(get_user_db),
):
    """搜索商品 - 带多个过滤条件."""
    return await item_service.search(
        db,
        keyword=keyword,
        category=category,
        min_price=min_price,
        max_price=max_price,
    )
```

### POST 创建资源

```python
@router.post("/", response_model=ItemResponse, status_code=201)
async def create_item(
    item_in: ItemCreate,
    db: AsyncSession = Depends(get_user_db),
    current_user: User = Depends(get_current_user),
):
    """创建新资源."""
    return await item_service.create(db, item_in, creator_id=current_user.id)
```

### PUT 更新资源

```python
@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    item_in: ItemUpdate,
    db: AsyncSession = Depends(get_user_db),
    current_user: User = Depends(get_current_user),
):
    """更新资源."""
    # 权限检查
    item = await item_service.get_by_id(db, item_id)
    if item.creator_id != current_user.id and not current_user.is_superuser:
        raise ForbiddenException("Not enough permissions")

    return await item_service.update(db, item_id, item_in)
```

### DELETE 删除资源

```python
@router.delete("/{item_id}", status_code=204)
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_user_db),
    current_user: User = Depends(get_current_user),
):
    """删除资源."""
    item = await item_service.get_by_id(db, item_id)
    if item.creator_id != current_user.id and not current_user.is_superuser:
        raise ForbiddenException("Not enough permissions")

    await item_service.delete(db, item_id)
    return None
```

### 文件上传

```python
from fastapi import UploadFile, File
import aiofiles

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传文件."""
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        raise ValidationException("File type not allowed")

    # 保存文件
    file_path = f"uploads/{file.filename}"
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    return {"filename": file.filename, "path": file_path}
```

---

## Service 层示例

### 基本 Service 类

```python
# app/services/item.py
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.crud.item import item_crud
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate


class ItemService:
    """商品服务类."""

    @staticmethod
    async def get_by_id(db: AsyncSession, item_id: int) -> Item:
        """获取单个商品."""
        item = await item_crud.get(db, id=item_id)
        if not item:
            raise NotFoundException(f"Item {item_id} not found")
        return item

    @staticmethod
    async def get_items(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> list[Item]:
        """获取商品列表."""
        return list(await item_crud.get_multi(db, skip=skip, limit=limit))

    @staticmethod
    async def get_count(db: AsyncSession) -> int:
        """获取商品总数."""
        return await item_crud.count(db)

    @staticmethod
    async def create(
        db: AsyncSession, 
        obj_in: ItemCreate,
        creator_id: int
    ) -> Item:
        """创建商品."""
        # 业务逻辑：检查 SKU 唯一性
        existing = await item_crud.get_by_sku(db, sku=obj_in.sku)
        if existing:
            raise ConflictException(f"SKU {obj_in.sku} already exists")

        # 添加创建者信息
        obj_in_data = obj_in.model_dump()
        obj_in_data["creator_id"] = creator_id

        return await item_crud.create_with_dict(db, obj_in_data)

    @staticmethod
    async def update(
        db: AsyncSession, 
        item_id: int, 
        obj_in: ItemUpdate
    ) -> Item:
        """更新商品."""
        item = await ItemService.get_by_id(db, item_id)

        # 业务逻辑：如果更新 SKU，检查唯一性
        if obj_in.sku and obj_in.sku != item.sku:
            existing = await item_crud.get_by_sku(db, sku=obj_in.sku)
            if existing:
                raise ConflictException(f"SKU {obj_in.sku} already exists")

        return await item_crud.update(db, db_obj=item, obj_in=obj_in)

    @staticmethod
    async def delete(db: AsyncSession, item_id: int) -> Item:
        """删除商品."""
        item = await ItemService.get_by_id(db, item_id)
        return await item_crud.delete(db, id=item_id)


item_service = ItemService()
```

### 带事务的 Service 方法

```python
from sqlalchemy import select
from sqlalchemy.ext.async import AsyncSession

@staticmethod
async def transfer_stock(
    db: AsyncSession,
    from_item_id: int,
    to_item_id: int,
    quantity: int
) -> tuple[Item, Item]:
    """转移库存 - 需要事务支持."""
    async with db.begin():  # 开启事务
        # 获取源商品
        from_item = await item_crud.get(db, id=from_item_id)
        if not from_item:
            raise NotFoundException(f"Source item {from_item_id} not found")

        if from_item.stock < quantity:
            raise ValidationException("Insufficient stock")

        # 获取目标商品
        to_item = await item_crud.get(db, id=to_item_id)
        if not to_item:
            raise NotFoundException(f"Target item {to_item_id} not found")

        # 更新库存
        from_item.stock -= quantity
        to_item.stock += quantity

        await db.flush()  # 刷新但不提交

    return from_item, to_item
```

### 批量操作

```python
@staticmethod
async def bulk_update_status(
    db: AsyncSession,
    item_ids: list[int],
    status: str
) -> int:
    """批量更新状态."""
    from sqlalchemy import update

    stmt = (
        update(Item)
        .where(Item.id.in_(item_ids))
        .values(status=status, updated_at=datetime.now(UTC))
    )

    result = await db.execute(stmt)
    await db.commit()

    return result.rowcount
```

---

## CRUD 操作示例

### 泛型 CRUD 基类

```python
# app/crud/base.py
from typing import Any, Generic, Sequence, TypeVar
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """通用 CRUD 基类."""

    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(
        self, 
        db: AsyncSession, 
        id: Any
    ) -> ModelType | None:
        """根据 ID 获取."""
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self, 
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> Sequence[ModelType]:
        """获取多条记录."""
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def count(self, db: AsyncSession) -> int:
        """获取总数."""
        result = await db.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar() or 0

    async def create(
        self, 
        db: AsyncSession, 
        obj_in: CreateSchemaType
    ) -> ModelType:
        """创建记录."""
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any]
    ) -> ModelType:
        """更新记录."""
        update_data = (
            obj_in if isinstance(obj_in, dict) 
            else obj_in.model_dump(exclude_unset=True)
        )

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self, 
        db: AsyncSession, 
        id: int
    ) -> ModelType | None:
        """删除记录."""
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
```

### 扩展 CRUD

```python
# app/crud/item.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate


class CRUDItem(CRUDBase[Item, ItemCreate, ItemUpdate]):
    """商品 CRUD."""

    async def get_by_sku(
        self, 
        db: AsyncSession, 
        sku: str
    ) -> Item | None:
        """根据 SKU 获取."""
        result = await db.execute(
            select(Item).where(Item.sku == sku)
        )
        return result.scalar_one_or_none()

    async def get_by_category(
        self, 
        db: AsyncSession, 
        category: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[Item]:
        """根据分类获取."""
        result = await db.execute(
            select(Item)
            .where(Item.category == category)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search(
        self,
        db: AsyncSession,
        keyword: str | None = None,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[Item]:
        """搜索商品."""
        query = select(Item)

        if keyword:
            query = query.where(
                Item.name.ilike(f"%{keyword}%") | 
                Item.description.ilike(f"%{keyword}%")
            )

        if category:
            query = query.where(Item.category == category)

        if min_price is not None:
            query = query.where(Item.price >= min_price)

        if max_price is not None:
            query = query.where(Item.price <= max_price)

        result = await db.execute(
            query.offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_active_items(
        self, 
        db: AsyncSession
    ) -> list[Item]:
        """获取上架商品."""
        result = await db.execute(
            select(Item).where(Item.is_active == True)
        )
        return list(result.scalars().all())


item_crud = CRUDItem(Item)
```

---

## 数据库查询示例

### 基本查询

```python
from sqlalchemy import select, and_, or_, not_
from sqlalchemy.ext.asyncio import AsyncSession

# 简单查询
result = await db.execute(select(User))
users = result.scalars().all()

# 条件查询
result = await db.execute(
    select(User).where(
        and_(
            User.is_active == True,
            User.email.like("%@example.com")
        )
    )
)

# OR 条件
result = await db.execute(
    select(User).where(
        or_(
            User.username == "admin",
            User.is_superuser == True
        )
    )
)
```

### 关联查询

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

# 预加载关系 (避免 N+1)
result = await db.execute(
    select(User)
    .options(selectinload(User.roles))
    .where(User.id == user_id)
)
user = result.scalar_one()

# 访问关系数据
roles = user.roles  # 不会再查询数据库

# 内连接查询
result = await db.execute(
    select(User, Role)
    .join(User.roles)
    .where(Role.name == "admin")
)

# 左连接查询
result = await db.execute(
    select(User, Role)
    .outerjoin(User.roles)
)
```

### 聚合查询

```python
from sqlalchemy import func, select

# 计数
result = await db.execute(
    select(func.count(User.id)).where(User.is_active == True)
)
active_count = result.scalar()

# 求和
result = await db.execute(
    select(func.sum(Order.total_amount))
    .where(Order.user_id == user_id)
)
total = result.scalar() or 0

# 分组统计
result = await db.execute(
    select(
        Order.status,
        func.count(Order.id).label("count"),
        func.sum(Order.total_amount).label("total")
    )
    .group_by(Order.status)
)
stats = result.all()
```

### 分页查询

```python
async def get_users_paginated(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10
) -> tuple[list[User], int]:
    """分页查询."""
    # 计算总数
    count_result = await db.execute(
        select(func.count(User.id))
    )
    total = count_result.scalar() or 0

    # 查询数据
    offset = (page - 1) * page_size
    result = await db.execute(
        select(User)
        .offset(offset)
        .limit(page_size)
        .order_by(User.created_at.desc())
    )
    users = list(result.scalars().all())

    return users, total
```

---

## 认证授权示例

### JWT Token 生成

```python
from datetime import UTC, datetime, timedelta
from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"

def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None
) -> str:
    """创建访问令牌."""
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(UTC),
    }

    return jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=ALGORITHM
    )
```

### Token 验证

```python
from jose import JWTError, jwt

def verify_token(token: str) -> str | None:
    """验证令牌并返回用户 ID."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        user_id: str | None = payload.get("sub")
        return user_id
    except JWTError:
        return None
```

### 密码处理

```python
import bcrypt

def get_password_hash(password: str) -> str:
    """生成密码哈希."""
    return bcrypt.hashpw(
        password.encode(), 
        bcrypt.gensalt()
    ).decode()


def verify_password(
    plain_password: str, 
    hashed_password: str
) -> bool:
    """验证密码."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )
```

### 依赖注入 - 获取当前用户

```python
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


async def get_current_user(
    db: AsyncSession = Depends(get_user_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """获取当前登录用户."""
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
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前超级管理员."""
    if not current_user.is_superuser:
        raise ForbiddenException("Not enough privileges")
    return current_user
```

---

## 错误处理示例

### 自定义异常类

```python
# app/core/exceptions.py
from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """API 基础异常."""
    def __init__(
        self, 
        status_code: int, 
        detail: str, 
        headers: dict | None = None
    ):
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers
        )


class NotFoundException(BaseAPIException):
    """资源未找到."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ConflictException(BaseAPIException):
    """资源冲突."""
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class UnauthorizedException(BaseAPIException):
    """未授权."""
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class ForbiddenException(BaseAPIException):
    """禁止访问."""
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class ValidationException(BaseAPIException):
    """验证错误."""
    def __init__(self, detail: str = "Validation error"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )
```

### 全局异常处理器

```python
# app/main.py
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


@app.exception_handler(BaseAPIException)
async def api_exception_handler(
    request: Request, 
    exc: BaseAPIException
):
    """处理 API 异常."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "error_type": type(exc).__name__
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request, 
    exc: Exception
):
    """处理未捕获的异常."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500
        }
    )
```

### 使用示例

```python
@router.get("/items/{item_id}")
async def get_item(item_id: int, db: AsyncSession = Depends(get_user_db)):
    item = await item_crud.get(db, id=item_id)
    if not item:
        raise NotFoundException(f"Item {item_id} not found")
    return item


@router.post("/items")
async def create_item(item_in: ItemCreate, db: AsyncSession = Depends(get_user_db)):
    existing = await item_crud.get_by_sku(db, sku=item_in.sku)
    if existing:
        raise ConflictException(f"SKU {item_in.sku} already exists")
    return await item_crud.create(db, obj_in=item_in)
```

---

## 测试示例

### 测试夹具 (Fixtures)

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
from app.core.security import get_password_hash

# 测试数据库 URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 创建测试引擎
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话."""
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """创建测试用户."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("Test1234"),
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def auth_headers(test_user: User) -> dict:
    """创建认证头."""
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}
```

### API 测试

```python
# tests/test_api/test_users.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """测试用户注册."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "username": "newuser",
            "password": "NewUser123"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_login_user(client: AsyncClient, test_user: User):
    """测试用户登录."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "Test1234"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data["data"]


@pytest.mark.asyncio
async def test_get_current_user(
    client: AsyncClient, 
    auth_headers: dict
):
    """测试获取当前用户."""
    response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["username"] == "testuser"


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """测试未授权访问."""
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401
```

### Service 层测试

```python
# tests/test_services/test_user_service.py
import pytest
from unittest.mock import AsyncMock, patch

from app.services.user import user_service
from app.schemas.user import UserCreate


@pytest.mark.asyncio
async def test_create_user_success(db: AsyncMock):
    """测试创建用户成功."""
    user_in = UserCreate(
        email="test@example.com",
        username="testuser",
        password="Test1234"
    )

    with patch("app.services.user.user_crud") as mock_crud:
        mock_crud.get_by_email.return_value = None
        mock_crud.get_by_username.return_value = None
        mock_crud.create.return_value = User(id=1, **user_in.model_dump())

        result = await user_service.create_user(db, user_in)

        assert result.email == "test@example.com"
        mock_crud.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_duplicate_email(db: AsyncMock):
    """测试创建用户 - 邮箱重复."""
    from app.core.exceptions import ConflictException

    user_in = UserCreate(
        email="existing@example.com",
        username="newuser",
        password="Test1234"
    )

    with patch("app.services.user.user_crud") as mock_crud:
        mock_crud.get_by_email.return_value = User(id=1)

        with pytest.raises(ConflictException):
            await user_service.create_user(db, user_in)
```

---

## CLI 命令示例

### 基本命令

```python
# app/cli/commands/items.py
import asyncio
import typer
from typing import Optional

app = typer.Typer(help="商品管理命令")


@app.command("list")
def list_items(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="分类"),
    limit: int = typer.Option(10, "--limit", "-l", help="显示数量"),
):
    """列出商品."""
    asyncio.run(_list_items(category, limit))


async def _list_items(category: Optional[str], limit: int):
    from app.db.session import UserSessionLocal
    from app.crud.item import item_crud

    async with UserSessionLocal() as db:
        if category:
            items = await item_crud.get_by_category(db, category, limit=limit)
        else:
            items = await item_crud.get_multi(db, limit=limit)

        for item in items:
            typer.echo(f"{item.id}: {item.name} - ${item.price}")


@app.command("create")
def create_item(
    name: str = typer.Option(..., "--name", "-n", help="商品名称"),
    sku: str = typer.Option(..., "--sku", "-s", help="SKU"),
    price: float = typer.Option(..., "--price", "-p", help="价格"),
):
    """创建商品."""
    asyncio.run(_create_item(name, sku, price))


async def _create_item(name: str, sku: str, price: float):
    from app.db.session import UserSessionLocal
    from app.crud.item import item_crud
    from app.schemas.item import ItemCreate

    async with UserSessionLocal() as db:
        item_in = ItemCreate(name=name, sku=sku, price=price)
        item = await item_crud.create(db, obj_in=item_in)
        typer.echo(f"Created item: {item.id} - {item.name}")
```

### 批量导入命令

```python
@app.command("import")
def import_items(
    file_path: str = typer.Option(..., "--file", "-f", help="CSV文件路径"),
    dry_run: bool = typer.Option(False, "--dry-run", help="模拟运行"),
):
    """批量导入商品."""
    asyncio.run(_import_items(file_path, dry_run))


async def _import_items(file_path: str, dry_run: bool):
    import csv
    from app.db.session import UserSessionLocal
    from app.crud.item import item_crud
    from app.schemas.item import ItemCreate

    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        items = list(reader)

    typer.echo(f"Found {len(items)} items to import")

    if dry_run:
        typer.echo("Dry run - no changes made")
        return

    async with UserSessionLocal() as db:
        created = 0
        skipped = 0

        for item_data in items:
            try:
                item_in = ItemCreate(**item_data)
                await item_crud.create(db, obj_in=item_in)
                created += 1
            except Exception as e:
                typer.echo(f"Skipping {item_data['sku']}: {e}")
                skipped += 1

        typer.echo(f"Created: {created}, Skipped: {skipped}")
```

---

## 附录

### 常用导入

```python
# FastAPI
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# SQLAlchemy
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload

# Pydantic
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

# 项目内部
from app.core.config import settings
from app.core.exceptions import *
from app.core.security import *
from app.db.session import *
from app.crud import *
from app.models import *
from app.schemas import *
from app.services import *
```

---

> 文档版本: 1.0.0
> 更新时间: 2026-03-24
