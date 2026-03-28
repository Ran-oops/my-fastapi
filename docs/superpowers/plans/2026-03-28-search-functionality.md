# 搜索功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现统一搜索功能，支持产品、订单、用户模块的全文搜索、搜索建议、搜索历史和结果高亮

**Architecture:** 使用PostgreSQL pg_trgm扩展实现全文搜索，通过GIN索引加速查询，采用DDD分层架构（Repository → Service → Router），统一搜索API端点支持多模块搜索

**Tech Stack:** FastAPI, SQLAlchemy 2.0, PostgreSQL, pg_trgm, Pydantic V2

---

## 文件结构

```
app/
├── modules/
│   ├── search/
│   │   ├── __init__.py
│   │   ├── models.py          # SearchHistory模型
│   │   ├── schemas.py         # 搜索请求/响应Schema
│   │   ├── repository.py      # 搜索数据库查询
│   │   ├── service.py         # 搜索业务逻辑
│   │   └── router.py          # 搜索API路由
│   ├── products/models.py     # 添加search_vector字段
│   ├── orders/models.py       # 添加search_vector字段
│   └── users/models.py        # 添加search_vector字段
├── common/
│   └── pagination.py          # 扩展PaginationParams
└── api/v1/__init__.py         # 注册搜索路由

alembic/versions/
└── xxx_add_search_functionality.py  # 数据库迁移

tests/
├── modules/
│   └── search/
│       ├── __init__.py
│       ├── conftest.py        # 测试fixtures
│       ├── test_search_service.py
│       ├── test_search_api.py
│       └── test_search_history.py
```

---

## Task 1: 数据库迁移和扩展安装

**Files:**
- Create: `alembic/versions/xxx_add_search_functionality.py`
- Modify: `app/modules/products/models.py`
- Modify: `app/modules/orders/models.py`
- Modify: `app/modules/users/models.py`
- Create: `app/modules/search/models.py`
- Create: `app/modules/search/__init__.py`

### Step 1: 创建搜索模块目录和__init__.py

```python
# app/modules/search/__init__.py
from app.modules.search.models import SearchHistory

__all__ = ["SearchHistory"]
```

### Step 2: 创建SearchHistory模型

```python
# app/modules/search/models.py
from __future__ import annotations

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

### Step 3: 添加search_vector字段到Product模型

```python
# app/modules/products/models.py
from sqlalchemy import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

class Product(UserBase):
    # ... 现有字段后添加 ...
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
```

### Step 4: 添加search_vector字段到Order模型

```python
# app/modules/orders/models.py
from sqlalchemy import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

class Order(UserBase):
    # ... 现有字段后添加 ...
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
```

### Step 5: 添加search_vector字段到User模型

```python
# app/modules/users/models.py
from sqlalchemy import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

class User(UserBase):
    # ... 现有字段后添加 ...
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
```

### Step 6: 创建Alembic迁移

```bash
alembic revision --autogenerate -m "add search functionality"
```

### Step 7: 编辑迁移文件添加pg_trgm扩展和触发器

```python
# alembic/versions/xxx_add_search_functionality.py
"""add search functionality

Revision ID: xxx
Revises: yyy
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'xxx'
down_revision = 'yyy'  # 替换为实际的前一个revision

def upgrade():
    # 1. 安装pg_trgm扩展
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    
    # 2. 添加search_vector列
    op.add_column('products', sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR, nullable=True))
    op.add_column('orders', sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR, nullable=True))
    op.add_column('users', sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR, nullable=True))
    
    # 3. 创建GIN索引
    op.execute('CREATE INDEX ix_products_search_vector ON products USING GIN(search_vector)')
    op.execute('CREATE INDEX ix_products_name_trgm ON products USING GIN(name gin_trgm_ops)')
    op.execute('CREATE INDEX ix_products_sku_trgm ON products USING GIN(sku gin_trgm_ops)')
    
    op.execute('CREATE INDEX ix_orders_search_vector ON orders USING GIN(search_vector)')
    op.execute('CREATE INDEX ix_orders_status_trgm ON orders USING GIN(status gin_trgm_ops)')
    
    op.execute('CREATE INDEX ix_users_search_vector ON users USING GIN(search_vector)')
    op.execute('CREATE INDEX ix_users_username_trgm ON users USING GIN(username gin_trgm_ops)')
    op.execute('CREATE INDEX ix_users_email_trgm ON users USING GIN(email gin_trgm_ops)')
    
    # 4. 创建触发器函数
    op.execute('''
        CREATE OR REPLACE FUNCTION product_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('simple', COALESCE(NEW.name, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(NEW.sku, '')), 'B') ||
                setweight(to_tsvector('simple', COALESCE(NEW.category, '')), 'C') ||
                setweight(to_tsvector('simple', COALESCE(NEW.description, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    ''')
    
    op.execute('''
        CREATE OR REPLACE FUNCTION order_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('simple', COALESCE(NEW.status, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(NEW.user_id::text, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    ''')
    
    op.execute('''
        CREATE OR REPLACE FUNCTION user_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('simple', COALESCE(NEW.username, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(NEW.email, '')), 'B') ||
                setweight(to_tsvector('simple', COALESCE(NEW.full_name, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    ''')
    
    # 5. 创建触发器
    op.execute('''
        CREATE TRIGGER product_search_vector_trigger
            BEFORE INSERT OR UPDATE ON products
            FOR EACH ROW EXECUTE FUNCTION product_search_vector_update()
    ''')
    
    op.execute('''
        CREATE TRIGGER order_search_vector_trigger
            BEFORE INSERT OR UPDATE ON orders
            FOR EACH ROW EXECUTE FUNCTION order_search_vector_update()
    ''')
    
    op.execute('''
        CREATE TRIGGER user_search_vector_trigger
            BEFORE INSERT OR UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION user_search_vector_update()
    ''')
    
    # 6. 回填现有数据的search_vector
    op.execute('''
        UPDATE products SET search_vector = 
            setweight(to_tsvector('simple', COALESCE(name, '')), 'A') ||
            setweight(to_tsvector('simple', COALESCE(sku, '')), 'B') ||
            setweight(to_tsvector('simple', COALESCE(category, '')), 'C') ||
            setweight(to_tsvector('simple', COALESCE(description, '')), 'D')
    ''')
    
    op.execute('''
        UPDATE orders SET search_vector = 
            setweight(to_tsvector('simple', COALESCE(status, '')), 'A') ||
            setweight(to_tsvector('simple', COALESCE(user_id::text, '')), 'B')
    ''')
    
    op.execute('''
        UPDATE users SET search_vector = 
            setweight(to_tsvector('simple', COALESCE(username, '')), 'A') ||
            setweight(to_tsvector('simple', COALESCE(email, '')), 'B') ||
            setweight(to_tsvector('simple', COALESCE(full_name, '')), 'C')
    ''')
    
    # 7. 创建search_history表
    op.create_table(
        'search_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('query', sa.String(200), nullable=False),
        sa.Column('search_type', sa.String(20), nullable=False),
        sa.Column('result_count', sa.Integer(), default=0, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_search_history_user_id', 'search_history', ['user_id'])
    op.create_index('ix_search_history_created_at', 'search_history', ['created_at'])


def downgrade():
    op.drop_index('ix_search_history_created_at', table_name='search_history')
    op.drop_index('ix_search_history_user_id', table_name='search_history')
    op.drop_table('search_history')
    
    op.execute('DROP TRIGGER IF EXISTS user_search_vector_trigger ON users')
    op.execute('DROP TRIGGER IF EXISTS order_search_vector_trigger ON orders')
    op.execute('DROP TRIGGER IF EXISTS product_search_vector_trigger ON products')
    
    op.execute('DROP FUNCTION IF EXISTS user_search_vector_update()')
    op.execute('DROP FUNCTION IF EXISTS order_search_vector_update()')
    op.execute('DROP FUNCTION IF EXISTS product_search_vector_update()')
    
    op.drop_index('ix_users_email_trgm', table_name='users')
    op.drop_index('ix_users_username_trgm', table_name='users')
    op.drop_index('ix_users_search_vector', table_name='users')
    
    op.drop_index('ix_orders_status_trgm', table_name='orders')
    op.drop_index('ix_orders_search_vector', table_name='orders')
    
    op.drop_index('ix_products_sku_trgm', table_name='products')
    op.drop_index('ix_products_name_trgm', table_name='products')
    op.drop_index('ix_products_search_vector', table_name='products')
    
    op.drop_column('users', 'search_vector')
    op.drop_column('orders', 'search_vector')
    op.drop_column('products', 'search_vector')
    
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')
```

### Step 8: 运行迁移验证

```bash
alembic upgrade head
```

### Step 9: 提交

```bash
git add app/modules/search/ app/modules/products/models.py app/modules/orders/models.py app/modules/users/models.py alembic/versions/
git commit -m "feat(search): add database models, migration, and pg_trgm extension"
```

---

## Task 2: 搜索Schema定义

**Files:**
- Create: `app/modules/search/schemas.py`

### Step 1: 创建搜索Schema

```python
# app/modules/search/schemas.py
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SearchHighlight(BaseModel):
    """搜索结果高亮"""
    model_config = ConfigDict(from_attributes=True)
    
    field_name: str
    highlighted: str


class SearchResultItem(BaseModel):
    """搜索结果项"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    type: str  # products/orders/users
    score: float
    data: dict[str, Any]  # 原始数据
    highlight: dict[str, str] | None = None  # 高亮字段


class SearchMeta(BaseModel):
    """搜索元数据"""
    total: int
    page: int
    page_size: int
    total_pages: int
    query: str
    search_type: str


class SearchResponse(BaseModel):
    """统一搜索响应"""
    model_config = ConfigDict(from_attributes=True)
    
    data: dict[str, list[SearchResultItem]]
    meta: SearchMeta


class SearchSuggestion(BaseModel):
    """搜索建议"""
    model_config = ConfigDict(from_attributes=True)
    
    text: str
    type: str
    score: float


class SearchSuggestionResponse(BaseModel):
    """搜索建议响应"""
    data: list[SearchSuggestion]


class SearchHistoryRead(BaseModel):
    """搜索历史读取"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    query: str
    search_type: str
    result_count: int
    created_at: str


class SearchHistoryResponse(BaseModel):
    """搜索历史响应"""
    data: list[SearchHistoryRead]
    total: int
    page: int
    page_size: int
    total_pages: int
```

### Step 2: 验证Schema定义

```bash
python -c "from app.modules.search.schemas import SearchResponse; print('Schema导入成功')"
```

### Step 3: 提交

```bash
git add app/modules/search/schemas.py
git commit -m "feat(search): add search schemas and response models"
```

---

## Task 3: 搜索Repository实现

**Files:**
- Create: `app/modules/search/repository.py`

### Step 1: 创建搜索Repository

```python
# app/modules/search/repository.py
from __future__ import annotations

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.products.models import Product
from app.modules.orders.models import Order
from app.modules.users.models import User
from app.modules.search.models import SearchHistory


class SearchRepository:
    """搜索数据访问层"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def search_products(
        self, 
        query: str, 
        skip: int = 0, 
        limit: int = 10,
        filters: dict | None = None
    ) -> tuple[list[Product], int]:
        """搜索产品"""
        # 构建基础查询
        stmt = select(Product)
        
        # 应用过滤条件
        if filters:
            if 'category' in filters:
                stmt = stmt.where(Product.category == filters['category'])
            if 'price_min' in filters:
                stmt = stmt.where(Product.price >= filters['price_min'])
            if 'price_max' in filters:
                stmt = stmt.where(Product.price <= filters['price_max'])
            if 'is_active' in filters:
                stmt = stmt.where(Product.is_active == filters['is_active'])
        
        # 搜索条件：使用trigram相似度
        similarity = func.similarity(Product.name, query)
        stmt = stmt.where(
            (similarity > 0.3) |
            Product.name.ilike(f'%{query}%') |
            Product.sku.ilike(f'%{query}%') |
            Product.description.ilike(f'%{query}%')
        )
        
        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)
        
        # 排序和分页
        stmt = stmt.order_by(similarity.desc())
        stmt = stmt.offset(skip).limit(limit)
        
        result = await self.session.execute(stmt)
        products = result.scalars().all()
        
        return products, total or 0
    
    async def search_orders(
        self, 
        query: str, 
        skip: int = 0, 
        limit: int = 10,
        filters: dict | None = None
    ) -> tuple[list[Order], int]:
        """搜索订单"""
        stmt = select(Order)
        
        # 应用过滤条件
        if filters:
            if 'status' in filters:
                stmt = stmt.where(Order.status == filters['status'])
            if 'user_id' in filters:
                stmt = stmt.where(Order.user_id == filters['user_id'])
            if 'date_from' in filters:
                stmt = stmt.where(Order.created_at >= filters['date_from'])
            if 'date_to' in filters:
                stmt = stmt.where(Order.created_at <= filters['date_to'])
        
        # 搜索条件：使用trigram相似度
        similarity = func.similarity(Order.status, query)
        stmt = stmt.where(
            (similarity > 0.3) |
            Order.status.ilike(f'%{query}%') |
            func.cast(Order.user_id, text('text')).ilike(f'%{query}%')
        )
        
        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)
        
        # 排序和分页
        stmt = stmt.order_by(similarity.desc())
        stmt = stmt.offset(skip).limit(limit)
        
        result = await self.session.execute(stmt)
        orders = result.scalars().all()
        
        return orders, total or 0
    
    async def search_users(
        self, 
        query: str, 
        skip: int = 0, 
        limit: int = 10,
        filters: dict | None = None
    ) -> tuple[list[User], int]:
        """搜索用户"""
        stmt = select(User)
        
        # 应用过滤条件
        if filters:
            if 'is_active' in filters:
                stmt = stmt.where(User.is_active == filters['is_active'])
        
        # 搜索条件：使用trigram相似度
        similarity = func.similarity(User.username, query)
        stmt = stmt.where(
            (similarity > 0.3) |
            User.username.ilike(f'%{query}%') |
            User.email.ilike(f'%{query}%') |
            User.full_name.ilike(f'%{query}%')
        )
        
        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)
        
        # 排序和分页
        stmt = stmt.order_by(similarity.desc())
        stmt = stmt.offset(skip).limit(limit)
        
        result = await self.session.execute(stmt)
        users = result.scalars().all()
        
        return users, total or 0
    
    async def get_suggestions(
        self, 
        query: str, 
        search_type: str, 
        limit: int = 5
    ) -> list[tuple[str, str, float]]:
        """获取搜索建议"""
        suggestions = []
        
        if search_type in ('all', 'products'):
            # 产品名称建议
            stmt = (
                select(
                    Product.name,
                    func.similarity(Product.name, query).label('score')
                )
                .where(func.similarity(Product.name, query) > 0.3)
                .order_by(func.similarity(Product.name, query).desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            for name, score in result:
                suggestions.append((name, 'products', score))
        
        if search_type in ('all', 'users'):
            # 用户名建议
            stmt = (
                select(
                    User.username,
                    func.similarity(User.username, query).label('score')
                )
                .where(func.similarity(User.username, query) > 0.3)
                .order_by(func.similarity(User.username, query).desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            for username, score in result:
                suggestions.append((username, 'users', score))
        
        # 按分数排序并返回前N个
        suggestions.sort(key=lambda x: x[2], reverse=True)
        return suggestions[:limit]
    
    async def save_search_history(
        self, 
        user_id: int, 
        query: str, 
        search_type: str, 
        result_count: int
    ) -> SearchHistory:
        """保存搜索历史（限制每个用户最多100条）"""
        # 保存新记录
        history = SearchHistory(
            user_id=user_id,
            query=query,
            search_type=search_type,
            result_count=result_count
        )
        self.session.add(history)
        await self.session.flush()  # 先flush获取ID
        
        # 检查并删除超过100条的旧记录
        count_stmt = (
            select(func.count())
            .select_from(SearchHistory)
            .where(SearchHistory.user_id == user_id)
        )
        total = await self.session.scalar(count_stmt)
        
        if total and total > 100:
            # 删除最旧的记录，保留100条
            delete_stmt = (
                select(SearchHistory)
                .where(SearchHistory.user_id == user_id)
                .order_by(SearchHistory.created_at.asc())
                .limit(total - 100)
            )
            result = await self.session.execute(delete_stmt)
            old_records = result.scalars().all()
            for record in old_records:
                await self.session.delete(record)
        
        await self.session.commit()
        await self.session.refresh(history)
        return history
    
    async def get_search_history(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 10
    ) -> tuple[list[SearchHistory], int]:
        """获取用户搜索历史"""
        stmt = (
            select(SearchHistory)
            .where(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        histories = result.scalars().all()
        
        # 计算总数
        count_stmt = (
            select(func.count())
            .select_from(SearchHistory)
            .where(SearchHistory.user_id == user_id)
        )
        total = await self.session.scalar(count_stmt)
        
        return histories, total or 0
    
    async def delete_search_history(
        self, 
        user_id: int, 
        history_id: int
    ) -> bool:
        """删除搜索历史"""
        stmt = (
            select(SearchHistory)
            .where(SearchHistory.id == history_id)
            .where(SearchHistory.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        history = result.scalar_one_or_none()
        
        if history:
            await self.session.delete(history)
            await self.session.commit()
            return True
        return False
    
    async def clear_search_history(self, user_id: int) -> int:
        """清空用户搜索历史"""
        from sqlalchemy import delete
        
        # 先获取数量
        count_stmt = (
            select(func.count())
            .select_from(SearchHistory)
            .where(SearchHistory.user_id == user_id)
        )
        count = await self.session.scalar(count_stmt) or 0
        
        # 使用DELETE语句直接删除
        delete_stmt = delete(SearchHistory).where(SearchHistory.user_id == user_id)
        await self.session.execute(delete_stmt)
        await self.session.commit()
        
        return count
```

### Step 2: 验证Repository导入

```bash
python -c "from app.modules.search.repository import SearchRepository; print('Repository导入成功')"
```

### Step 3: 提交

```bash
git add app/modules/search/repository.py
git commit -m "feat(search): add search repository with full-text search queries"
```

---

## Task 4: 搜索Service实现

**Files:**
- Create: `app/modules/search/service.py`

### Step 1: 创建搜索Service

```python
# app/modules/search/service.py
from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PaginationParams
from app.modules.search.repository import SearchRepository
from app.modules.search.schemas import (
    SearchResponse,
    SearchMeta,
    SearchResultItem,
    SearchSuggestion,
    SearchSuggestionResponse,
    SearchHistoryRead,
)


class SearchService:
    """搜索业务逻辑层"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = SearchRepository(session)
    
    def _highlight_text(self, text: str, query: str) -> str:
        """高亮匹配文本"""
        if not text or not query:
            return text
        
        # 使用正则表达式匹配（不区分大小写）
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return pattern.sub(f'<mark>{query}</mark>', text)
    
    def _calculate_score(self, item: dict, query: str, weights: dict) -> float:
        """计算相关性得分"""
        score = 0.0
        
        for field, weight in weights.items():
            value = str(getattr(item, field, '') or '')
            if query.lower() in value.lower():
                score += weight
        
        return min(score, 1.0)
    
    async def search(
        self,
        query: str,
        search_type: str,
        user_id: int,
        pagination: PaginationParams,
        filters: dict | None = None
    ) -> SearchResponse:
        """统一搜索"""
        if not query or not query.strip():
            raise ValueError("搜索关键词不能为空")
        
        if search_type not in ('all', 'products', 'orders', 'users'):
            raise ValueError("无效的搜索类型，可选值: products, orders, users, all")
        
        data = {}
        total = 0
        
        # 搜索产品
        if search_type in ('all', 'products'):
            products, product_total = await self.repository.search_products(
                query=query,
                skip=pagination.skip,
                limit=pagination.limit,
                filters=filters
            )
            
            product_items = []
            product_weights = {'name': 1.0, 'sku': 0.8, 'category': 0.5, 'description': 0.3}
            
            for product in products:
                score = self._calculate_score(product, query, product_weights)
                highlight = {}
                
                if query.lower() in (product.name or '').lower():
                    highlight['name'] = self._highlight_text(product.name, query)
                if query.lower() in (product.sku or '').lower():
                    highlight['sku'] = self._highlight_text(product.sku, query)
                if query.lower() in (product.description or '').lower():
                    highlight['description'] = self._highlight_text(product.description, query)
                
                product_items.append(SearchResultItem(
                    id=product.id,
                    type='products',
                    score=score,
                    data={
                        'id': product.id,
                        'name': product.name,
                        'sku': product.sku,
                        'price': float(product.price),
                        'category': product.category,
                        'is_active': product.is_active,
                    },
                    highlight=highlight if highlight else None
                ))
            
            data['products'] = product_items
            total += product_total
        
        # 搜索订单
        if search_type in ('all', 'orders'):
            orders, order_total = await self.repository.search_orders(
                query=query,
                skip=pagination.skip,
                limit=pagination.limit,
                filters=filters
            )
            
            order_items = []
            
            for order in orders:
                score = 0.8 if query.lower() in (order.status or '').lower() else 0.3
                highlight = {}
                
                if query.lower() in (order.status or '').lower():
                    highlight['status'] = self._highlight_text(order.status, query)
                
                order_items.append(SearchResultItem(
                    id=order.id,
                    type='orders',
                    score=score,
                    data={
                        'id': order.id,
                        'status': order.status,
                        'user_id': order.user_id,
                        'total_amount': float(order.total_amount),
                        'created_at': order.created_at.isoformat() if order.created_at else None,
                    },
                    highlight=highlight if highlight else None
                ))
            
            data['orders'] = order_items
            total += order_total
        
        # 搜索用户
        if search_type in ('all', 'users'):
            users, user_total = await self.repository.search_users(
                query=query,
                skip=pagination.skip,
                limit=pagination.limit,
                filters=filters
            )
            
            user_items = []
            user_weights = {'username': 1.0, 'email': 0.9, 'full_name': 0.7}
            
            for user in users:
                score = self._calculate_score(user, query, user_weights)
                highlight = {}
                
                if query.lower() in (user.username or '').lower():
                    highlight['username'] = self._highlight_text(user.username, query)
                if query.lower() in (user.email or '').lower():
                    highlight['email'] = self._highlight_text(user.email, query)
                if query.lower() in (user.full_name or '').lower():
                    highlight['full_name'] = self._highlight_text(user.full_name, query)
                
                user_items.append(SearchResultItem(
                    id=user.id,
                    type='users',
                    score=score,
                    data={
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'full_name': user.full_name,
                        'is_active': user.is_active,
                    },
                    highlight=highlight if highlight else None
                ))
            
            data['users'] = user_items
            total += user_total
        
        # 计算总页数
        total_pages = (total + pagination.page_size - 1) // pagination.page_size
        
        # 保存搜索历史
        await self.repository.save_search_history(
            user_id=user_id,
            query=query,
            search_type=search_type,
            result_count=total
        )
        
        return SearchResponse(
            data=data,
            meta=SearchMeta(
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                query=query,
                search_type=search_type
            )
        )
    
    async def suggest(
        self,
        query: str,
        search_type: str = 'all',
        limit: int = 5
    ) -> SearchSuggestionResponse:
        """获取搜索建议"""
        if len(query) < 2:
            return SearchSuggestionResponse(data=[])
        
        suggestions = await self.repository.get_suggestions(
            query=query,
            search_type=search_type,
            limit=limit
        )
        
        return SearchSuggestionResponse(
            data=[
                SearchSuggestion(text=text, type=s_type, score=score)
                for text, s_type, score in suggestions
            ]
        )
    
    async def get_history(
        self,
        user_id: int,
        pagination: PaginationParams
    ) -> dict:
        """获取搜索历史"""
        histories, total = await self.repository.get_search_history(
            user_id=user_id,
            skip=pagination.skip,
            limit=pagination.limit
        )
        
        total_pages = (total + pagination.page_size - 1) // pagination.page_size
        
        return {
            'data': [
                SearchHistoryRead(
                    id=h.id,
                    query=h.query,
                    search_type=h.search_type,
                    result_count=h.result_count,
                    created_at=h.created_at.isoformat() if h.created_at else None
                )
                for h in histories
            ],
            'total': total,
            'page': pagination.page,
            'page_size': pagination.page_size,
            'total_pages': total_pages
        }
    
    async def delete_history(
        self,
        user_id: int,
        history_id: int
    ) -> bool:
        """删除搜索历史"""
        return await self.repository.delete_search_history(user_id, history_id)
    
    async def clear_history(
        self,
        user_id: int
    ) -> int:
        """清空搜索历史"""
        return await self.repository.clear_search_history(user_id)
```

### Step 2: 验证Service导入

```bash
python -c "from app.modules.search.service import SearchService; print('Service导入成功')"
```

### Step 3: 提交

```bash
git add app/modules/search/service.py
git commit -m "feat(search): add search service with highlighting and history"
```

---

## Task 5: 搜索API路由实现

**Files:**
- Create: `app/modules/search/router.py`

### Step 1: 创建搜索API路由

```python
# app/modules/search/router.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_session
from app.common.pagination import PaginationParams
from app.modules.users.models import User
from app.modules.search.service import SearchService
from app.modules.search.schemas import (
    SearchResponse,
    SearchSuggestionResponse,
)


router = APIRouter()


@router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="搜索关键词"),
    type: str = Query("all", description="搜索模块: products/orders/users/all"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    category: str | None = Query(None, description="产品分类过滤"),
    price_min: float | None = Query(None, description="最低价格"),
    price_max: float | None = Query(None, description="最高价格"),
    is_active: bool | None = Query(None, description="是否激活"),
    status: str | None = Query(None, description="订单状态过滤"),
    user_id: int | None = Query(None, description="用户ID过滤"),
    date_from: str | None = Query(None, description="开始日期"),
    date_to: str | None = Query(None, description="结束日期"),
    sort_by: str = Query("relevance", description="排序方式: relevance/price/created_at"),
    sort_order: str = Query("desc", description="排序顺序: asc/desc"),
    session: AsyncSession = Depends(get_user_session),
    current_user: User = Depends(get_current_user),
):
    """统一搜索端点"""
    try:
        service = SearchService(session)
        pagination = PaginationParams(page=page, page_size=page_size)
        
        # 构建过滤条件
        filters = {}
        if category:
            filters['category'] = category
        if price_min is not None:
            filters['price_min'] = price_min
        if price_max is not None:
            filters['price_max'] = price_max
        if is_active is not None:
            filters['is_active'] = is_active
        if status:
            filters['status'] = status
        if user_id is not None:
            filters['user_id'] = user_id
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        
        return await service.search(
            query=q,
            search_type=type,
            user_id=current_user.id,
            pagination=pagination,
            filters=filters if filters else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/suggest", response_model=SearchSuggestionResponse)
async def suggest(
    q: str = Query(..., min_length=2, description="搜索关键词（至少2字符）"),
    type: str = Query("all", description="搜索模块"),
    limit: int = Query(5, ge=1, le=20, description="返回建议数量"),
    session: AsyncSession = Depends(get_user_session),
    current_user: User = Depends(get_current_user),
):
    """获取搜索建议"""
    service = SearchService(session)
    return await service.suggest(
        query=q,
        search_type=type,
        limit=limit
    )


@router.get("/history")
async def get_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_user_session),
    current_user: User = Depends(get_current_user),
):
    """获取搜索历史"""
    service = SearchService(session)
    pagination = PaginationParams(page=page, page_size=page_size)
    return await service.get_history(
        user_id=current_user.id,
        pagination=pagination
    )


@router.delete("/history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(
    history_id: int,
    session: AsyncSession = Depends(get_user_session),
    current_user: User = Depends(get_current_user),
):
    """删除搜索历史"""
    service = SearchService(session)
    deleted = await service.delete_history(
        user_id=current_user.id,
        history_id=history_id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="搜索历史不存在"
        )
    return None


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(
    session: AsyncSession = Depends(get_user_session),
    current_user: User = Depends(get_current_user),
):
    """清空搜索历史"""
    service = SearchService(session)
    await service.clear_history(user_id=current_user.id)
    return None
```

### Step 2: 验证Router导入

```bash
python -c "from app.modules.search.router import router; print('Router导入成功')"
```

### Step 3: 提交

```bash
git add app/modules/search/router.py
git commit -m "feat(search): add search API endpoints with filtering and history"
```

---

## Task 6: 注册搜索路由

**Files:**
- Modify: `app/api/v1/__init__.py`

### Step 1: 添加搜索路由导入

```python
# app/api/v1/__init__.py
from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.config.router import router as config_router
from app.modules.exports.router import router as exports_router
from app.modules.notifications.router import router as notifications_router
from app.modules.orders.router import router as orders_router
from app.modules.products.router import router as products_router
from app.modules.roles.router import router as roles_router
from app.modules.users.auth_router import router as auth_router
from app.modules.users.user_router import router as users_router
from app.modules.search.router import router as search_router  # 添加这行
from app.tasks.router import router as tasks_router


api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(roles_router, tags=["roles", "permissions"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(exports_router, prefix="/exports", tags=["exports"])
api_router.include_router(search_router, prefix="/search", tags=["search"])  # 添加这行
```

### Step 2: 验证路由注册

```bash
python -c "from app.api.v1 import api_router; print([r.path for r in api_router.routes])"
```

### Step 3: 提交

```bash
git add app/api/v1/__init__.py
git commit -m "feat(search): register search router in API v1"
```

---

## Task 7: 扩展PaginationParams

**Files:**
- Modify: `app/common/pagination.py`

### Step 1: 添加page_size最大值验证

```python
# app/common/pagination.py
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.common.schemas import ListResponse


T = TypeVar("T")


class PaginationParams(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)  # 添加le=100

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(ListResponse[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
```

### Step 2: 验证PaginationParams

```bash
python -c "from app.common.pagination import PaginationParams; p = PaginationParams(page=1, page_size=150); print(p.page_size)"
```

### Step 3: 提交

```bash
git add app/common/pagination.py
git commit -m "feat(search): add page_size max validation to PaginationParams"
```

---

## Task 8: 搜索Service测试

**Files:**
- Create: `tests/modules/search/__init__.py`
- Create: `tests/modules/search/conftest.py`
- Create: `tests/modules/search/test_search_service.py`

### Step 1: 创建测试目录和__init__.py

```python
# tests/modules/search/__init__.py
```

### Step 2: 创建测试fixtures

```python
# tests/modules/search/conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.products.models import Product
from app.modules.orders.models import Order
from app.modules.users.models import User
from app.modules.search.models import SearchHistory


@pytest.fixture
async def sample_products(db_session: AsyncSession):
    """创建测试产品数据"""
    products = [
        Product(
            name="手机壳",
            sku="CASE-001",
            description="适用于iPhone的手机壳",
            price=99.99,
            category="配件",
            is_active=True
        ),
        Product(
            name="手机充电器",
            sku="CHARGER-001",
            description="快速充电器",
            price=199.99,
            category="配件",
            is_active=True
        ),
        Product(
            name="笔记本电脑",
            sku="LAPTOP-001",
            description="高性能笔记本",
            price=9999.99,
            category="电脑",
            is_active=True
        ),
    ]
    
    for product in products:
        db_session.add(product)
    await db_session.commit()
    
    for product in products:
        await db_session.refresh(product)
    
    return products


@pytest.fixture
async def sample_users(db_session: AsyncSession):
    """创建测试用户数据"""
    users = [
        User(
            username="admin",
            email="admin@example.com",
            full_name="管理员",
            hashed_password="hashed",
            is_active=True
        ),
        User(
            username="user1",
            email="user1@example.com",
            full_name="用户一",
            hashed_password="hashed",
            is_active=True
        ),
    ]
    
    for user in users:
        db_session.add(user)
    await db_session.commit()
    
    for user in users:
        await db_session.refresh(user)
    
    return users
```

### Step 3: 创建Service测试

```python
# tests/modules/search/test_search_service.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PaginationParams
from app.modules.search.service import SearchService


@pytest.mark.asyncio
class TestSearchService:
    """搜索服务测试"""
    
    async def test_search_products(
        self, 
        db_session: AsyncSession, 
        sample_products
    ):
        """测试产品搜索"""
        service = SearchService(db_session)
        pagination = PaginationParams(page=1, page_size=10)
        
        result = await service.search(
            query="手机",
            search_type="products",
            user_id=1,
            pagination=pagination
        )
        
        assert "products" in result.data
        assert len(result.data["products"]) > 0
        assert result.meta.query == "手机"
        assert result.meta.search_type == "products"
    
    async def test_search_empty_query(
        self, 
        db_session: AsyncSession
    ):
        """测试空查询"""
        service = SearchService(db_session)
        pagination = PaginationParams(page=1, page_size=10)
        
        with pytest.raises(ValueError, match="搜索关键词不能为空"):
            await service.search(
                query="",
                search_type="all",
                user_id=1,
                pagination=pagination
            )
    
    async def test_search_invalid_type(
        self, 
        db_session: AsyncSession
    ):
        """测试无效搜索类型"""
        service = SearchService(db_session)
        pagination = PaginationParams(page=1, page_size=10)
        
        with pytest.raises(ValueError, match="无效的搜索类型"):
            await service.search(
                query="test",
                search_type="invalid",
                user_id=1,
                pagination=pagination
            )
    
    async def test_suggest(
        self, 
        db_session: AsyncSession, 
        sample_products
    ):
        """测试搜索建议"""
        service = SearchService(db_session)
        
        result = await service.suggest(
            query="手机",
            search_type="products",
            limit=5
        )
        
        assert len(result.data) <= 5
        for suggestion in result.data:
            assert suggestion.text
            assert suggestion.type in ("products", "users")
            assert 0 <= suggestion.score <= 1
    
    async def test_suggest_min_length(
        self, 
        db_session: AsyncSession
    ):
        """测试搜索建议最小长度"""
        service = SearchService(db_session)
        
        result = await service.suggest(
            query="a",  # 只有1个字符
            search_type="all",
            limit=5
        )
        
        assert len(result.data) == 0
```

### Step 4: 运行测试

```bash
pytest tests/modules/search/test_search_service.py -v
```

### Step 5: 提交

```bash
git add tests/modules/search/
git commit -m "test(search): add search service unit tests"
```

---

## Task 9: 搜索API测试

**Files:**
- Create: `tests/modules/search/test_search_api.py`

### Step 1: 创建API测试

```python
# tests/modules/search/test_search_api.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestSearchAPI:
    """搜索API测试"""
    
    async def test_search_endpoint(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        sample_products
    ):
        """测试搜索端点"""
        response = await client.get(
            "/api/v1/search",
            params={"q": "手机", "type": "products"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert data["meta"]["query"] == "手机"
    
    async def test_search_without_auth(
        self, 
        client: AsyncClient
    ):
        """测试未认证搜索"""
        response = await client.get(
            "/api/v1/search",
            params={"q": "手机"}
        )
        
        assert response.status_code == 401
    
    async def test_search_empty_query(
        self, 
        client: AsyncClient, 
        auth_headers: dict
    ):
        """测试空查询"""
        response = await client.get(
            "/api/v1/search",
            params={"q": ""},
            headers=auth_headers
        )
        
        assert response.status_code == 400
    
    async def test_suggest_endpoint(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        sample_products
    ):
        """测试搜索建议端点"""
        response = await client.get(
            "/api/v1/search/suggest",
            params={"q": "手机", "limit": 3},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) <= 3
    
    async def test_suggest_min_length(
        self, 
        client: AsyncClient, 
        auth_headers: dict
    ):
        """测试搜索建议最小长度"""
        response = await client.get(
            "/api/v1/search/suggest",
            params={"q": "a"},  # 只有1个字符
            headers=auth_headers
        )
        
        assert response.status_code == 422  # 验证错误
    
    async def test_history_endpoint(
        self, 
        client: AsyncClient, 
        auth_headers: dict
    ):
        """测试搜索历史端点"""
        response = await client.get(
            "/api/v1/search/history",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    async def test_delete_history(
        self, 
        client: AsyncClient, 
        auth_headers: dict
    ):
        """测试删除搜索历史"""
        response = await client.delete(
            "/api/v1/search/history/1",
            headers=auth_headers
        )
        
        assert response.status_code == 204
    
    async def test_clear_history(
        self, 
        client: AsyncClient, 
        auth_headers: dict
    ):
        """测试清空搜索历史"""
        response = await client.delete(
            "/api/v1/search/history",
            headers=auth_headers
        )
        
        assert response.status_code == 204
```

### Step 2: 运行测试

```bash
pytest tests/modules/search/test_search_api.py -v
```

### Step 3: 提交

```bash
git add tests/modules/search/test_search_api.py
git commit -m "test(search): add search API integration tests"
```

---

## Task 10: 搜索历史测试

**Files:**
- Create: `tests/modules/search/test_search_history.py`

### Step 1: 创建搜索历史测试

```python
# tests/modules/search/test_search_history.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PaginationParams
from app.modules.search.service import SearchService


@pytest.mark.asyncio
class TestSearchHistory:
    """搜索历史测试"""
    
    async def test_save_search_history(
        self, 
        db_session: AsyncSession, 
        sample_products
    ):
        """测试保存搜索历史"""
        service = SearchService(db_session)
        pagination = PaginationParams(page=1, page_size=10)
        
        # 执行搜索会自动保存历史
        await service.search(
            query="手机",
            search_type="products",
            user_id=1,
            pagination=pagination
        )
        
        # 获取历史
        history = await service.get_history(
            user_id=1,
            pagination=pagination
        )
        
        assert history["total"] > 0
        assert len(history["data"]) > 0
        assert history["data"][0].query == "手机"
    
    async def test_get_history_pagination(
        self, 
        db_session: AsyncSession, 
        sample_products
    ):
        """测试搜索历史分页"""
        service = SearchService(db_session)
        
        # 执行多次搜索
        for i in range(5):
            pagination = PaginationParams(page=1, page_size=10)
            await service.search(
                query=f"测试{i}",
                search_type="products",
                user_id=1,
                pagination=pagination
            )
        
        # 获取第一页
        pagination = PaginationParams(page=1, page_size=2)
        history = await service.get_history(
            user_id=1,
            pagination=pagination
        )
        
        assert history["total"] == 5
        assert len(history["data"]) == 2
        assert history["page"] == 1
        assert history["page_size"] == 2
    
    async def test_delete_history(
        self, 
        db_session: AsyncSession, 
        sample_products
    ):
        """测试删除搜索历史"""
        service = SearchService(db_session)
        pagination = PaginationParams(page=1, page_size=10)
        
        # 执行搜索
        await service.search(
            query="手机",
            search_type="products",
            user_id=1,
            pagination=pagination
        )
        
        # 获取历史ID
        history = await service.get_history(user_id=1, pagination=pagination)
        history_id = history["data"][0].id
        
        # 删除历史
        deleted = await service.delete_history(user_id=1, history_id=history_id)
        assert deleted is True
        
        # 验证已删除
        history_after = await service.get_history(user_id=1, pagination=pagination)
        assert history_after["total"] == 0
    
    async def test_clear_history(
        self, 
        db_session: AsyncSession, 
        sample_products
    ):
        """测试清空搜索历史"""
        service = SearchService(db_session)
        
        # 执行多次搜索
        for i in range(3):
            pagination = PaginationParams(page=1, page_size=10)
            await service.search(
                query=f"测试{i}",
                search_type="products",
                user_id=1,
                pagination=pagination
            )
        
        # 清空历史
        count = await service.clear_history(user_id=1)
        assert count == 3
        
        # 验证已清空
        pagination = PaginationParams(page=1, page_size=10)
        history = await service.get_history(user_id=1, pagination=pagination)
        assert history["total"] == 0
```

### Step 2: 运行测试

```bash
pytest tests/modules/search/test_search_history.py -v
```

### Step 3: 提交

```bash
git add tests/modules/search/test_search_history.py
git commit -m "test(search): add search history tests"
```

---

## Task 11: 集成测试和验证

**Files:**
- Modify: `tests/modules/search/conftest.py`

### Step 1: 运行所有搜索测试

```bash
pytest tests/modules/search/ -v --cov=app.modules.search --cov-report=term-missing
```

### Step 2: 运行linting检查

```bash
just lint
```

### Step 3: 运行类型检查

```bash
uvx ty check app
```

### Step 4: 修复发现的问题

根据测试和检查结果修复任何问题。

### Step 5: 最终提交

```bash
git add .
git commit -m "feat(search): complete search functionality implementation"
```

---

## 完成清单

- [ ] Task 1: 数据库迁移和扩展安装
- [ ] Task 2: 搜索Schema定义
- [ ] Task 3: 搜索Repository实现
- [ ] Task 4: 搜索Service实现
- [ ] Task 5: 搜索API路由实现
- [ ] Task 6: 注册搜索路由
- [ ] Task 7: 扩展PaginationParams
- [ ] Task 8: 搜索Service测试
- [ ] Task 9: 搜索API测试
- [ ] Task 10: 搜索历史测试
- [ ] Task 11: 集成测试和验证
