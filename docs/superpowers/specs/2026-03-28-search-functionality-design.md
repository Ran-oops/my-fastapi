# 搜索功能设计文档

**日期**: 2026-03-28
**状态**: 待审核

## 1. 架构概览

### 整体架构

```text
┌─────────────────────────────────────────────────────────┐
│                    统一搜索API                           │
│                    /api/v1/search                        │
├─────────────────────────────────────────────────────────┤
│                  SearchService                           │
│  ┌─────────────┬─────────────┬─────────────┐           │
│  │ ProductSearch│ OrderSearch │ UserSearch  │           │
│  └─────────────┴─────────────┴─────────────┘           │
├─────────────────────────────────────────────────────────┤
│                  SearchRepository                        │
│  ┌─────────────────────────────────────────┐           │
│  │         SearchAdapter (抽象层)            │           │
│  ├─────────────────────────────────────────┤           │
│  │ PostgreSQLAdapter │   SQLiteAdapter     │           │
│  │ (pg_trgm + GIN)   │   (LIKE + 索引)      │           │
│  └─────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

### 关键设计决策

- **统一入口**: `/api/v1/search` 作为唯一搜索端点
- **模块过滤**: 通过 `type` 参数指定搜索模块(products/orders/users/all)
- **分层架构**: Router → Service → Repository → Adapter → Database
- **异步支持**: 所有搜索操作使用 `async/await`
- **数据库兼容**: 通过适配器层支持 PostgreSQL(生产)和 SQLite(开发)

## 2. API设计

### 统一搜索端点

```text
GET /api/v1/search?q={query}&type={module}&page={page}&page_size={size}
```

**认证:** 需要JWT认证(通过 `get_current_user`)

**参数说明:**

| 参数      | 必填 | 类型   | 默认值 | 说明                                |
| --------- | ---- | ------ | ------ | ----------------------------------- |
| q         | 是   | string | -      | 搜索关键词                          |
| type      | 否   | string | all    | 搜索模块: products/orders/users/all |
| page      | 否   | int    | 1      | 页码                                |
| page_size | 否   | int    | 10     | 每页数量(最大100)                   |

**分页规则:**

- 当 `type=all` 时：每个模块返回 `page_size` 条结果，总计最多 `page_size * 3` 条
- 当 `type=products` 时：只返回产品的 `page_size` 条结果
- `meta.total` 表示当前搜索类型的总结果数

**响应结构(type=all):**

```json
{
  "data": {
    "products": [
      {
        "id": 1,
        "name": "手机壳",
        "sku": "CASE-001",
        "score": 0.85,
        "highlight": {
          "name": "<mark>手机</mark>壳"
        }
      }
    ],
    "orders": [...],
    "users": [...]
  },
  "meta": {
    "total": 150,
    "page": 1,
    "page_size": 10,
    "total_pages": 15,
    "query": "手机",
    "search_type": "all"
  }
}
```

**响应结构(type=products):**

```json
{
  "data": {
    "products": [...]
  },
  "meta": {
    "total": 50,
    "page": 1,
    "page_size": 10,
    "total_pages": 5,
    "query": "手机",
    "search_type": "products"
  }
}
```

**注意:** 当指定具体模块时，`data` 只包含该模块的结果，其他模块不包含在响应中。

**响应格式说明:** 搜索API使用自定义响应格式(`data` + `meta`)，与现有 `DataResponse`/`PaginatedResponse` 不同。这是因为搜索结果需要返回多个模块的数据，且每个结果包含 `score` 和 `highlight` 字段。

### 搜索建议端点

```text
GET /api/v1/search/suggest?q={query}&type={module}&limit={limit}
```

**认证:** 需要JWT认证(通过 `get_current_user`)

**参数说明:**

| 参数  | 必填 | 类型   | 默认值 | 说明                  |
| ----- | ---- | ------ | ------ | --------------------- |
| q     | 是   | string | -      | 搜索关键词(至少2字符) |
| type  | 否   | string | all    | 搜索模块              |
| limit | 否   | int    | 5      | 返回建议数量          |

**响应结构:**

```json
{
  "data": [
    {
      "text": "手机壳",
      "type": "products",
      "score": 0.92
    },
    {
      "text": "手机配件",
      "type": "products",
      "score": 0.85
    }
  ]
}
```

### 搜索历史端点

```text
GET    /api/v1/search/history
DELETE /api/v1/search/history/{id}
DELETE /api/v1/search/history
```

**认证方式:** 所有历史端点需要JWT认证，通过 `get_current_user` 依赖获取当前用户ID。

## 3. 数据模型

### 数据库兼容性

搜索功能需支持两种数据库，通过适配器层实现：

```text
app/modules/search/
├── adapters/
│   ├── __init__.py
│   ├── base.py          # BaseSearchAdapter 抽象基类
│   ├── postgresql.py    # PostgreSQL 适配器
│   └── sqlite.py        # SQLite 适配器
├── repository.py        # 调用适配器，不关心数据库细节
└── ...
```

**适配器接口(BaseSearchAdapter):**

```python
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession

class BaseSearchAdapter(ABC):
    """搜索适配器抽象基类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    @abstractmethod
    async def search_products(
        self, 
        query: str, 
        skip: int = 0, 
        limit: int = 10,
        filters: dict | None = None
    ) -> tuple[list, int]:
        """搜索产品，返回 (结果列表, 总数)"""
        pass

    @abstractmethod
    async def search_orders(
        self, 
        query: str, 
        skip: int = 0, 
        limit: int = 10,
        filters: dict | None = None
    ) -> tuple[list, int]:
        """搜索订单"""
        pass

    @abstractmethod
    async def search_users(
        self, 
        query: str, 
        skip: int = 0, 
        limit: int = 10,
        filters: dict | None = None
    ) -> tuple[list, int]:
        """搜索用户"""
        pass

    @abstractmethod
    async def get_suggestions(
        self, 
        query: str, 
        search_type: str, 
        limit: int = 5
    ) -> list[tuple[str, str, float]]:
        """获取搜索建议，返回 [(文本, 类型, 相似度得分)]"""
        pass
```

### PostgreSQL扩展(仅生产环境)

```sql
-- Alembic迁移中添加(仅PostgreSQL)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 模型变更

**search_vector列(两种数据库通用):**

- PostgreSQL: 使用 TEXT 类型，数据库触发器自动填充
- SQLite: 使用 TEXT 类型，应用层填充

**说明:** 使用 TEXT 类型而不是 TSVECTOR，以兼容 SQLite。PostgreSQL 触发器会将内容转换为 tsvector 进行索引。

**适配器实现细节:**

PostgreSQL 适配器：

- 使用 `func.similarity()` 进行 trigram 相似度搜索
- 使用 GIN 索引加速查询
- 使用 `to_tsvector` 和 `to_tsquery` 进行全文搜索

SQLite 适配器：

- 使用 `LIKE` 或 `ILIKE` 进行模糊匹配
- 使用普通 B-tree 索引
- 应用层计算相似度得分

**GIN索引(仅PostgreSQL):**

```sql
-- 为产品表创建GIN索引
CREATE INDEX ix_products_search_vector ON products USING GIN(search_vector);
CREATE INDEX ix_products_name_trgm ON products USING GIN(name gin_trgm_ops);
CREATE INDEX ix_products_sku_trgm ON products USING GIN(sku gin_trgm_ops);

-- 为订单表创建GIN索引
CREATE INDEX ix_orders_search_vector ON orders USING GIN(search_vector);
CREATE INDEX ix_orders_status_trgm ON orders USING GIN(status gin_trgm_ops);

-- 为用户表创建GIN索引
CREATE INDEX ix_users_search_vector ON users USING GIN(search_vector);
CREATE INDEX ix_users_username_trgm ON users USING GIN(username gin_trgm_ops);
CREATE INDEX ix_users_email_trgm ON users USING GIN(email gin_trgm_ops);
```

**普通索引(SQLite通用):**

```sql
-- SQLite使用普通B-tree索引
CREATE INDEX ix_products_name ON products(name);
CREATE INDEX ix_products_sku ON products(sku);
CREATE INDEX ix_orders_status ON orders(status);
CREATE INDEX ix_users_username ON users(username);
CREATE INDEX ix_users_email ON users(email);
```

**PaginationParams扩展:**

在 `app/common/pagination.py` 中添加 `page_size` 最大值验证：

```python
class PaginationParams(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
```

#### Product模型

在 `app/modules/products/models.py` 中添加:

```python
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

class Product(UserBase):
    # ... 现有字段 ...
    # search_vector: PostgreSQL使用TSVECTOR，SQLite使用TEXT
    search_vector: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Product search_vector填充(数据库触发器 - 仅PostgreSQL):**

```sql
CREATE OR REPLACE FUNCTION product_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('simple', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.sku, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(NEW.category, '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(NEW.description, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER product_search_vector_trigger
    BEFORE INSERT OR UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION product_search_vector_update();
```

**Product search_vector填充(应用层 - SQLite):**

在 `app/modules/products/service.py` 的 `create_product` 和 `update_product` 方法中添加：

```python
def update_search_vector(product: Product) -> None:
    """应用层填充search_vector(SQLite兼容)"""
    parts = []
    if product.name:
        parts.append(product.name)
    if product.sku:
        parts.append(product.sku)
    if product.category:
        parts.append(product.category)
    if product.description:
        parts.append(product.description)
    product.search_vector = ' '.join(parts)
```

#### Order模型

在 `app/modules/orders/models.py` 中添加:

```python
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

class Order(UserBase):
    # ... 现有字段 ...
    search_vector: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Order search_vector填充(数据库触发器 - 仅PostgreSQL):**

```sql
CREATE OR REPLACE FUNCTION order_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('simple', COALESCE(NEW.status, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.user_id::text, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER order_search_vector_trigger
    BEFORE INSERT OR UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION order_search_vector_update();
```

**Order search_vector填充(应用层 - SQLite):**

在 `app/modules/orders/service.py` 中添加：

```python
def update_search_vector(order: Order) -> None:
    """应用层填充search_vector(SQLite兼容)"""
    parts = []
    if order.status:
        parts.append(order.status)
    if order.user_id:
        parts.append(str(order.user_id))
    order.search_vector = ' '.join(parts)
```

#### User模型

在 `app/modules/users/models.py` 中添加:

```python
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

class User(UserBase):
    # ... 现有字段 ...
    search_vector: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**User search_vector填充(数据库触发器 - 仅PostgreSQL):**

```sql
CREATE OR REPLACE FUNCTION user_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('simple', COALESCE(NEW.username, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.email, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(NEW.full_name, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_search_vector_trigger
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION user_search_vector_update();
```

**User search_vector填充(应用层 - SQLite):**

在 `app/modules/users/service.py` 中添加：

```python
def update_search_vector(user: User) -> None:
    """应用层填充search_vector(SQLite兼容)"""
    parts = []
    if user.username:
        parts.append(user.username)
    if user.email:
        parts.append(user.email)
    if user.full_name:
        parts.append(user.full_name)
    user.search_vector = ' '.join(parts)
```

### 新增搜索历史表

```python
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import UserBase

class SearchHistory(UserBase):
    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    query: Mapped[str] = mapped_column(String(200), nullable=False)
    search_type: Mapped[str] = mapped_column(String(20), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
```

**注意:** SearchHistory使用 `UserBase` 作为基类，因为它存储在用户数据库中，需要时间戳字段。

## 4. 服务层设计

### SearchService核心方法

```python
class SearchService:
    async def search(
        self, 
        session: AsyncSession, 
        query: str, 
        search_type: str,
        user_id: int,
        pagination: PaginationParams
    ) -> SearchResponse

    async def suggest(
        self, 
        session: AsyncSession, 
        query: str, 
        search_type: str,
        limit: int = 5
    ) -> list[SearchSuggestion]

    async def get_history(
        self,
        session: AsyncSession,
        user_id: int,
        pagination: PaginationParams
    ) -> PaginatedResponse[SearchHistoryRead]

    async def delete_history(
        self,
        session: AsyncSession,
        user_id: int,
        history_id: int
    ) -> None

    async def clear_history(
        self,
        session: AsyncSession,
        user_id: int
    ) -> None
```

### 响应结构说明

**当 `type=all` 时:**

```json
{
  "data": {
    "products": [...],
    "orders": [...],
    "users": [...]
  },
  "meta": {...}
}
```

**当 `type=products` 时:**

```json
{
  "data": {
    "products": [...]
  },
  "meta": {...}
}
```

**注意:** 当指定具体模块时，`data` 只包含该模块的结果，其他模块不包含在响应中。

### 搜索策略(适配器实现)

**PostgreSQL 适配器策略(三级降级):**

1. **精确匹配**: 查询与字段完全一致时优先返回
2. **Trigram相似度**: 使用 `similarity()` 函数，阈值 > 0.3
3. **ILIKE模糊匹配**: 最后降级方案

**SQLite 适配器策略(两级降级):**

1. **精确匹配**: 查询与字段完全一致时优先返回
2. **LIKE模糊匹配**: 使用 `LIKE` 进行模糊匹配

**适配器工厂:**

```python
# app/modules/search/adapters/__init__.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.search.adapters.base import BaseSearchAdapter
from app.modules.search.adapters.postgresql import PostgreSQLSearchAdapter
from app.modules.search.adapters.sqlite import SQLiteSearchAdapter

def create_search_adapter(session: AsyncSession) -> BaseSearchAdapter:
    """根据数据库类型创建对应的搜索适配器"""
    dialect = session.bind.dialect.name

    if dialect == 'postgresql':
        return PostgreSQLSearchAdapter(session)
    elif dialect == 'sqlite':
        return SQLiteSearchAdapter(session)
    else:
        # 默认使用 SQLite 适配器(兼容性最好)
        return SQLiteSearchAdapter(session)
```

### 搜索字段权重

| 模块 | 高权重字段                  | 低权重字段                        | 说明                   |
| ---- | --------------------------- | --------------------------------- | ---------------------- |
| 产品 | name (1.0), sku (0.8)       | description (0.3), category (0.5) | 支持完整文本搜索       |
| 订单 | status (0.8)                | user_id (0.5)                     | 仅支持状态和用户ID搜索 |
| 用户 | username (1.0), email (0.9) | full_name (0.7)                   | 支持用户名/邮箱搜索    |

**订单搜索限制说明:** 当前Order模型仅包含status和user_id字段，搜索能力有限。如需扩展订单搜索(如按产品名称、收货地址搜索)，需要在Order模型中添加相关字段或关联OrderItem表。

### 相关性排序

- 使用 `similarity()` 计算相似度得分
- 结合字段权重计算综合得分
- 按得分降序排列

## 5. 高级功能

### 搜索建议/自动补全

- 输入2个字符后触发建议
- 返回最相关的5条建议
- 缓存策略：使用Redis缓存热门搜索键(复用现有Celery Redis基础设施)，缓存有效期5分钟

### 搜索结果高亮

每个搜索结果包含 `highlight` 字段，包含匹配文本的高亮版本：

```json
{
  "data": {
    "products": [
      {
        "id": 1,
        "name": "手机壳",
        "sku": "CASE-001",
        "score": 0.85,
        "highlight": {
          "name": "<mark>手机</mark>壳",
          "description": "适用于iPhone的<mark>手机</mark>壳"
        }
      }
    ]
  }
}
```

- `highlight` 是每个结果对象的可选字段
- 使用 `<mark>` 标签包裹匹配文本
- 只包含有匹配的字段

### 高级过滤和排序

所有过滤和排序参数都是 `/api/v1/search` 端点的查询参数。

**产品过滤参数(type=products时可用):**

```text
GET /api/v1/search?q=手机&type=products
  &category=配件
  &price_min=10&price_max=100
  &is_active=true
  &sort_by=relevance|price|created_at
  &sort_order=asc|desc
```

**订单过滤参数(type=orders时可用):**

```text
GET /api/v1/search?q=待发货&type=orders
  &status=PENDING|CONFIRMED|SHIPPED|COMPLETED|CANCELLED
  &user_id=123
  &date_from=2026-01-01&date_to=2026-12-31
  &sort_by=relevance|created_at
  &sort_order=asc|desc
```

**说明:** `date_from` 和 `date_to` 过滤的是 `created_at` 字段(来自 `TimestampMixin`)。

**用户过滤参数(type=users时可用):**

```text
GET /api/v1/search?q=admin&type=users
  &is_active=true
  &sort_by=relevance|created_at
  &sort_order=asc|desc
```

### 搜索历史

- 自动保存用户搜索记录
- 限制每个用户最多100条
- 支持删除单条或清空历史

### 错误处理

| 错误场景       | HTTP状态码 | 错误信息                                               |
| -------------- | ---------- | ------------------------------------------------------ |
| 空查询         | 400        | "搜索关键词不能为空"                                   |
| 无效type参数   | 400        | "无效的搜索类型，可选值: products, orders, users, all" |
| 搜索超时(>3秒) | 504        | "搜索请求超时，请稍后重试"                             |

## 6. 测试策略

### 单元测试

- `SearchService` 方法测试(模拟数据库)
- 搜索建议逻辑测试
- 过滤和排序逻辑测试

### 集成测试

- 搜索API端点测试
- 数据库查询测试
- 搜索历史CRUD测试

### 测试用例示例

```python
# 测试产品搜索
async def test_search_products():
    response = await client.get("/api/v1/search?q=手机&type=products")
    assert response.status_code == 200
    assert len(response.json()["data"]["products"]) > 0

# 测试搜索建议
async def test_search_suggestions():
    response = await client.get("/api/v1/search/suggest?q=手&type=products")
    assert response.status_code == 200
    assert len(response.json()["data"]) <= 5

# 测试空查询
async def test_search_empty_query():
    response = await client.get("/api/v1/search")
    assert response.status_code == 400
```

### 性能测试

- 搜索响应时间目标 < 500ms(10万条数据)
- 搜索超时保护 > 3秒(返回504错误)
- 并发搜索测试(10个并发请求)

**说明:** 500ms是性能目标，3秒是超时保护。正常情况应达到500ms以内，超过3秒表示系统异常。

## 7. 文件结构

```text
app/
├── modules/
│   └── search/
│       ├── __init__.py
│       ├── models.py          # SearchHistory模型
│       ├── schemas.py         # 搜索请求/响应Schema
│       ├── adapters/
│       │   ├── __init__.py    # 适配器工厂
│       │   ├── base.py        # BaseSearchAdapter 抽象基类
│       │   ├── postgresql.py  # PostgreSQL 适配器
│       │   └── sqlite.py      # SQLite 适配器
│       ├── repository.py      # 搜索数据访问层(调用适配器)
│       ├── service.py         # 搜索业务逻辑
│       └── router.py          # 搜索API路由
└── db/
    └── migrations/
        └── xxx_add_search.py  # Alembic迁移(添加search_vector列)
```

## 8. 实现顺序

1. 创建SearchHistory模型和迁移
2. 为现有模型添加search_vector列(TEXT类型，兼容两种数据库)
3. 实现搜索适配器抽象基类(BaseSearchAdapter)
4. 实现PostgreSQL适配器(PostgreSQLSearchAdapter)
5. 实现SQLite适配器(SQLiteSearchAdapter)
6. 实现适配器工厂(create_search_adapter)
7. 实现SearchRepository(调用适配器)
8. 实现SearchService
9. 实现搜索API路由
10. 在 `app/api/v1/__init__.py` 注册搜索路由
11. 添加搜索建议功能
12. 添加搜索历史功能
13. 实现结果高亮
14. 编写测试(同时测试SQLite和PostgreSQL适配器)
