from __future__ import annotations

from sqlalchemy import asc, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.orders.models import Order
from app.modules.products.models import Product
from app.modules.search.adapters.base import BaseSearchAdapter
from app.modules.users.models import User


class PostgreSQLSearchAdapter(BaseSearchAdapter):
    """PostgreSQL 搜索适配器，使用 pg_trgm 全文搜索"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def _get_sort_column(self, model, sort_by: str, similarity):
        """获取排序列"""
        if sort_by == "relevance":
            return similarity.desc()
        elif sort_by == "price" and hasattr(model, "price"):
            return model.price
        elif sort_by == "created_at" and hasattr(model, "created_at"):
            return model.created_at
        return similarity.desc()

    async def search_products(
        self, query: str, skip: int = 0, limit: int = 10, filters: dict | None = None
    ) -> tuple[list[Product], int]:
        """搜索产品 - PostgreSQL 实现"""
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

        # 搜索条件：使用trigram相似度
        similarity = func.similarity(Product.name, query)
        stmt = stmt.where(
            (similarity > 0.3)
            | Product.name.ilike(f"%{query}%")
            | Product.sku.ilike(f"%{query}%")
            | Product.description.ilike(f"%{query}%")
        )

        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        # 排序和分页
        sort_by = filters.get("sort_by", "relevance") if filters else "relevance"
        sort_order = filters.get("sort_order", "desc") if filters else "desc"

        sort_column = self._get_sort_column(Product, sort_by, similarity)
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
        """搜索订单 - PostgreSQL 实现"""
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

        # 搜索条件：使用trigram相似度
        similarity = func.similarity(Order.status, query)
        stmt = stmt.where(
            (similarity > 0.3)
            | Order.status.ilike(f"%{query}%")
            | func.cast(Order.user_id, text("text")).ilike(f"%{query}%")
        )

        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        # 排序和分页
        sort_by = filters.get("sort_by", "relevance") if filters else "relevance"
        sort_order = filters.get("sort_order", "desc") if filters else "desc"

        sort_column = self._get_sort_column(Order, sort_by, similarity)
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
        """搜索用户 - PostgreSQL 实现"""
        stmt = select(User)

        # 应用过滤条件
        if filters:
            if "is_active" in filters:
                stmt = stmt.where(User.is_active == filters["is_active"])

        # 搜索条件：使用trigram相似度
        similarity = func.similarity(User.username, query)
        stmt = stmt.where(
            (similarity > 0.3)
            | User.username.ilike(f"%{query}%")
            | User.email.ilike(f"%{query}%")
            | User.full_name.ilike(f"%{query}%")
        )

        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        # 排序和分页
        sort_by = filters.get("sort_by", "relevance") if filters else "relevance"
        sort_order = filters.get("sort_order", "desc") if filters else "desc"

        sort_column = self._get_sort_column(User, sort_by, similarity)
        if sort_order == "asc":
            stmt = stmt.order_by(asc(sort_column))
        else:
            stmt = stmt.order_by(desc(sort_column))

        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return users, total or 0

    async def get_suggestions(self, query: str, search_type: str, limit: int = 5) -> list[tuple[str, str, float]]:
        """获取搜索建议 - PostgreSQL 实现"""
        suggestions = []

        if search_type in ("all", "products"):
            # 产品名称建议
            stmt = (
                select(Product.name, func.similarity(Product.name, query).label("score"))
                .where(func.similarity(Product.name, query) > 0.3)
                .order_by(func.similarity(Product.name, query).desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            for name, score in result:
                suggestions.append((name, "products", score))

        if search_type in ("all", "users"):
            # 用户名建议
            stmt = (
                select(User.username, func.similarity(User.username, query).label("score"))
                .where(func.similarity(User.username, query) > 0.3)
                .order_by(func.similarity(User.username, query).desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            for username, score in result:
                suggestions.append((username, "users", score))

        # 按分数排序并返回前N个
        suggestions.sort(key=lambda x: x[2], reverse=True)
        return suggestions[:limit]
