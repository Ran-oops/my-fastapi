# 搜索功能设计文档

**日期**: 2026-03-28
**状态**: 待审核

## 1. 架构概览

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    统一搜索API                           │
│                    /api/v1/search                        │
├─────────────────────────────────────────────────────────┤
│                  SearchService                           │
│  ┌─────────────┬─────────────┬─────────────┐           │
│  │ ProductSearch│ OrderSearch │ UserSearch  │           │
│  └─────────────┴─────────────┴─────────────┘           │
├─────────────────────────────────────────────────────────┤
│              SearchRepository                           │
│  ┌─────────────────────────────────────────┐           │
│  │ PostgreSQL + pg_trgm + GIN Index        │           │
│  └─────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

### 关键设计决策

- **统一入口**: `/api/v1/search` 作为唯一搜索端点
- **模块过滤**: 通过 `type` 参数指定搜索模块（products/orders/users/all）
- **分层架构**: Repository → Service → Router，符合现有DDD模式
- **异步支持**: 所有搜索操作使用 `async/await`

## 2. API设计

### 统一搜索端点

```
GET /api/v1/search?q={query}&type={module}&page={page}&page_size={size}
```

**参数说明:**

| 参数 | 必填 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| q | 是 | string | - | 搜索关键词 |
| type | 否 | string | all | 搜索模块: products/orders/users/all |
| page | 否 | int | 1 | 页码 |
| page_size | 否 | int | 10 | 每页数量（最大100） |

**响应结构:**

```json
{
  "data": {
    "products": [...],
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

### 搜索建议端点

```
GET /api/v1/search/suggest?q={query}&type={module}&limit={limit}
```

**参数说明:**

| 参数 | 必填 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| q | 是 | string | - | 搜索关键词（至少2字符） |
| type | 否 | string | all | 搜索模块 |
| limit | 否 | int | 5 | 返回建议数量 |

### 搜索历史端点

```
GET    /api/v1/search/history
DELETE /api/v1/search/history/{id}
DELETE /api/v1/search/history
```

## 3. 数据模型

### PostgreSQL扩展

```sql
-- Alembic迁移中添加
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
```

### 模型变更

#### Product模型

在 `app/modules/products/models.py` 中添加:

```python
from sqlalchemy import Column, TSVECTOR

class Product(UserBase):
    # ... 现有字段 ...
    search_vector = Column(TSVECTOR)
```

#### Order模型

在 `app/modules/orders/models.py` 中添加:

```python
class Order(UserBase):
    # ... 现有字段 ...
    search_vector = Column(TSVECTOR)
```

#### User模型

在 `app/modules/users/models.py` 中添加:

```python
class User(UserBase):
    # ... 现有字段 ...
    search_vector = Column(TSVECTOR)
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
```

### 搜索策略（三级降级）

1. **精确匹配**: 查询与字段完全一致时优先返回
2. **Trigram相似度**: 使用 `similarity()` 函数，阈值 > 0.3
3. **ILIKE模糊匹配**: 最后降级方案

### 搜索字段权重

| 模块 | 高权重字段 | 低权重字段 |
|------|-----------|-----------|
| 产品 | name (1.0), sku (0.8) | description (0.3), category (0.5) |
| 订单 | status (0.8) | user_id (0.5) |
| 用户 | username (1.0), email (0.9) | full_name (0.7) |

### 相关性排序

- 使用 `similarity()` 计算相似度得分
- 结合字段权重计算综合得分
- 按得分降序排列

## 5. 高级功能

### 搜索建议/自动补全

- 输入2个字符后触发建议
- 返回最相关的5条建议
- 缓存热门搜索词（Redis或内存）

### 搜索结果高亮

```json
{
  "highlight": {
    "name": "<mark>手机</mark>壳",
    "description": "适用于iPhone的<mark>手机</mark>壳"
  }
}
```

- 使用 `<mark>` 标签包裹匹配文本
- 支持多字段高亮

### 高级过滤和排序

```
GET /api/v1/search?q=手机&type=products
  &category=配件
  &price_min=10&price_max=100
  &sort_by=relevance|price|created_at
  &sort_order=asc|desc
```

### 搜索历史

- 自动保存用户搜索记录
- 限制每个用户最多100条
- 支持删除单条或清空历史

### 错误处理

| 错误场景 | HTTP状态码 | 错误信息 |
|----------|-----------|----------|
| 空查询 | 400 | "搜索关键词不能为空" |
| 无效type参数 | 400 | "无效的搜索类型，可选值: products, orders, users, all" |
| 搜索超时（>3秒） | 504 | "搜索请求超时，请稍后重试" |

## 6. 测试策略

### 单元测试

- `SearchService` 方法测试（模拟数据库）
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

- 搜索响应时间 < 500ms（10万条数据）
- 并发搜索测试（10个并发请求）

## 7. 文件结构

```
app/
├── modules/
│   └── search/
│       ├── __init__.py
│       ├── models.py          # SearchHistory模型
│       ├── schemas.py         # 搜索请求/响应Schema
│       ├── repository.py      # 搜索数据库查询
│       ├── service.py         # 搜索业务逻辑
│       └── router.py          # 搜索API路由
└── db/
    └── migrations/
        └── xxx_add_search.py  # Alembic迁移（添加pg_trgm扩展和search_vector列）
```

## 8. 实现顺序

1. 安装PostgreSQL扩展（pg_trgm, unaccent）
2. 创建SearchHistory模型和迁移
3. 为现有模型添加search_vector列
4. 实现SearchRepository
5. 实现SearchService
6. 实现搜索API路由
7. 添加搜索建议功能
8. 添加搜索历史功能
9. 实现结果高亮
10. 编写测试
