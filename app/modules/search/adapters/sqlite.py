from __future__ import annotations

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.orders.models import Order
from app.modules.products.models import Product
from app.modules.search.adapters.base import BaseSearchAdapter
from app.modules.users.models import User


class SQLiteSearchAdapter(BaseSearchAdapter):
    """SQLite 搜索适配器，使用 LIKE 模糊匹配"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def _calculate_similarity(self, text: str, query: str) -> float:
        """计算相似度得分（应用层实现）"""
        if not text or not query:
            return 0.0

        text_lower = text.lower()
        query_lower = query.lower()

        # 精确匹配
        if text_lower == query_lower:
            return 1.0

        # 包含匹配
        if query_lower in text_lower:
            return 0.8

        # 前缀匹配
        if text_lower.startswith(query_lower):
            return 0.6

        # 模糊匹配（简单实现）
        # 计算公共子序列长度
        common_len = 0
        for i in range(min(len(text_lower), len(query_lower))):
            if text_lower[i] == query_lower[i]:
                common_len += 1
            else:
                break

        if common_len > 0:
            return 0.3 + (common_len / max(len(text_lower), len(query_lower))) * 0.3

        return 0.0

    def _get_sort_column(self, model, sort_by: str):
        """获取排序列"""
        if sort_by == "price" and hasattr(model, "price"):
            return model.price
        elif sort_by == "created_at" and hasattr(model, "created_at"):
            return model.created_at
        return model.id  # 默认按ID排序

    async def search_products(
        self, query: str, skip: int = 0, limit: int = 10, filters: dict | None = None
    ) -> tuple[list[Product], int]:
        """搜索产品 - SQLite 实现"""
        stmt = select(Product)

        # 应用过滤条件
        if filters:
            if "category" in filters:
                stmt = stmt.where(Product.category == filters["category"])
            if "price_min" in filters:
                stmt = stmt.where(Product.price >= filters["price_min"])
            if "price_max" in filters:
                stmt = stmt.where(Product.price <= filters["price_max"])
            if "is_active" in filters:
                stmt = stmt.where(Product.is_active == filters["is_active"])

        # 搜索条件：使用 LIKE 模糊匹配
        search_pattern = f"%{query}%"
        stmt = stmt.where(
            Product.name.ilike(search_pattern)
            | Product.sku.ilike(search_pattern)
            | Product.description.ilike(search_pattern)
            | Product.category.ilike(search_pattern)
        )

        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        # 排序和分页
        sort_by = filters.get("sort_by", "relevance") if filters else "relevance"
        sort_order = filters.get("sort_order", "desc") if filters else "desc"

        if sort_by == "relevance":
            # SQLite 不支持 trigram，按创建时间排序
            stmt = stmt.order_by(desc(Product.created_at))
        else:
            sort_column = self._get_sort_column(Product, sort_by)
            if sort_order == "asc":
                stmt = stmt.order_by(asc(sort_column))
            else:
                stmt = stmt.order_by(desc(sort_column))

        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        products = result.scalars().all()

        return products, total or 0

    async def search_orders(
        self, query: str, skip: int = 0, limit: int = 10, filters: dict | None = None
    ) -> tuple[list[Order], int]:
        """搜索订单 - SQLite 实现"""
        stmt = select(Order)

        # 应用过滤条件
        if filters:
            if "status" in filters:
                stmt = stmt.where(Order.status == filters["status"])
            if "user_id" in filters:
                stmt = stmt.where(Order.user_id == filters["user_id"])
            if "date_from" in filters:
                stmt = stmt.where(Order.created_at >= filters["date_from"])
            if "date_to" in filters:
                stmt = stmt.where(Order.created_at <= filters["date_to"])

        # 搜索条件：使用 LIKE 模糊匹配
        search_pattern = f"%{query}%"
        stmt = stmt.where(
            Order.status.ilike(search_pattern) | func.cast(Order.user_id, func.text()).ilike(search_pattern)
        )

        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        # 排序和分页
        sort_by = filters.get("sort_by", "relevance") if filters else "relevance"
        sort_order = filters.get("sort_order", "desc") if filters else "desc"

        if sort_by == "relevance":
            stmt = stmt.order_by(desc(Order.created_at))
        else:
            sort_column = self._get_sort_column(Order, sort_by)
            if sort_order == "asc":
                stmt = stmt.order_by(asc(sort_column))
            else:
                stmt = stmt.order_by(desc(sort_column))

        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        orders = result.scalars().all()

        return orders, total or 0

    async def search_users(
        self, query: str, skip: int = 0, limit: int = 10, filters: dict | None = None
    ) -> tuple[list[User], int]:
        """搜索用户 - SQLite 实现"""
        stmt = select(User)

        # 应用过滤条件
        if filters:
            if "is_active" in filters:
                stmt = stmt.where(User.is_active == filters["is_active"])

        # 搜索条件：使用 LIKE 模糊匹配
        search_pattern = f"%{query}%"
        stmt = stmt.where(
            User.username.ilike(search_pattern)
            | User.email.ilike(search_pattern)
            | User.full_name.ilike(search_pattern)
        )

        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        # 排序和分页
        sort_by = filters.get("sort_by", "relevance") if filters else "relevance"
        sort_order = filters.get("sort_order", "desc") if filters else "desc"

        if sort_by == "relevance":
            stmt = stmt.order_by(desc(User.created_at))
        else:
            sort_column = self._get_sort_column(User, sort_by)
            if sort_order == "asc":
                stmt = stmt.order_by(asc(sort_column))
            else:
                stmt = stmt.order_by(desc(sort_column))

        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return users, total or 0

    async def get_suggestions(self, query: str, search_type: str, limit: int = 5) -> list[tuple[str, str, float]]:
        """获取搜索建议 - SQLite 实现"""
        suggestions = []

        if search_type in ("all", "products"):
            # 产品名称建议
            stmt = select(Product.name).where(Product.name.ilike(f"%{query}%")).limit(limit)
            result = await self.session.execute(stmt)
            for (name,) in result:
                score = self._calculate_similarity(name, query)
                suggestions.append((name, "products", score))

        if search_type in ("all", "users"):
            # 用户名建议
            stmt = select(User.username).where(User.username.ilike(f"%{query}%")).limit(limit)
            result = await self.session.execute(stmt)
            for (username,) in result:
                score = self._calculate_similarity(username, query)
                suggestions.append((username, "users", score))

        # 按分数排序并返回前N个
        suggestions.sort(key=lambda x: x[2], reverse=True)
        return suggestions[:limit]
