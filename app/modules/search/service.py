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

        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return pattern.sub(f"<mark>{query}</mark>", text)

    def _calculate_score(self, item: dict, query: str, weights: dict) -> float:
        """计算相关性得分"""
        score = 0.0

        for field, weight in weights.items():
            value = str(getattr(item, field, "") or "")
            if query.lower() in value.lower():
                score += weight

        return min(score, 1.0)

    async def search(
        self,
        query: str,
        search_type: str,
        user_id: int,
        pagination: PaginationParams,
        filters: dict | None = None,
    ) -> SearchResponse:
        """统一搜索"""
        if not query or not query.strip():
            raise ValueError("搜索关键词不能为空")

        if search_type not in ("all", "products", "orders", "users"):
            raise ValueError("无效的搜索类型，可选值: products, orders, users, all")

        data = {}
        total = 0

        if search_type in ("all", "products"):
            products, product_total = await self.repository.search_products(
                query=query,
                skip=pagination.skip,
                limit=pagination.limit,
                filters=filters,
            )

            product_items = []
            product_weights = {"name": 1.0, "sku": 0.8, "category": 0.5, "description": 0.3}

            for product in products:
                score = self._calculate_score(product, query, product_weights)
                highlight = {}

                if query.lower() in (product.name or "").lower():
                    highlight["name"] = self._highlight_text(product.name, query)
                if query.lower() in (product.sku or "").lower():
                    highlight["sku"] = self._highlight_text(product.sku, query)
                if query.lower() in (product.description or "").lower():
                    highlight["description"] = self._highlight_text(product.description, query)

                product_items.append(
                    SearchResultItem(
                        id=product.id,
                        type="products",
                        score=score,
                        data={
                            "id": product.id,
                            "name": product.name,
                            "sku": product.sku,
                            "price": float(product.price),
                            "category": product.category,
                            "is_active": product.is_active,
                        },
                        highlight=highlight if highlight else None,
                    )
                )

            data["products"] = product_items
            total += product_total

        if search_type in ("all", "orders"):
            orders, order_total = await self.repository.search_orders(
                query=query,
                skip=pagination.skip,
                limit=pagination.limit,
                filters=filters,
            )

            order_items = []

            for order in orders:
                score = 0.8 if query.lower() in (order.status or "").lower() else 0.3
                highlight = {}

                if query.lower() in (order.status or "").lower():
                    highlight["status"] = self._highlight_text(order.status, query)

                order_items.append(
                    SearchResultItem(
                        id=order.id,
                        type="orders",
                        score=score,
                        data={
                            "id": order.id,
                            "status": order.status,
                            "user_id": order.user_id,
                            "total_amount": float(order.total_amount),
                            "created_at": order.created_at.isoformat() if order.created_at else None,
                        },
                        highlight=highlight if highlight else None,
                    )
                )

            data["orders"] = order_items
            total += order_total

        if search_type in ("all", "users"):
            users, user_total = await self.repository.search_users(
                query=query,
                skip=pagination.skip,
                limit=pagination.limit,
                filters=filters,
            )

            user_items = []
            user_weights = {"username": 1.0, "email": 0.9, "full_name": 0.7}

            for user in users:
                score = self._calculate_score(user, query, user_weights)
                highlight = {}

                if query.lower() in (user.username or "").lower():
                    highlight["username"] = self._highlight_text(user.username, query)
                if query.lower() in (user.email or "").lower():
                    highlight["email"] = self._highlight_text(user.email, query)
                if query.lower() in (user.full_name or "").lower():
                    highlight["full_name"] = self._highlight_text(user.full_name, query)

                user_items.append(
                    SearchResultItem(
                        id=user.id,
                        type="users",
                        score=score,
                        data={
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "full_name": user.full_name,
                            "is_active": user.is_active,
                        },
                        highlight=highlight if highlight else None,
                    )
                )

            data["users"] = user_items
            total += user_total

        total_pages = (total + pagination.page_size - 1) // pagination.page_size

        await self.repository.save_search_history(
            user_id=user_id,
            query=query,
            search_type=search_type,
            result_count=total,
        )

        return SearchResponse(
            data=data,
            meta=SearchMeta(
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                query=query,
                search_type=search_type,
            ),
        )

    async def suggest(
        self,
        query: str,
        search_type: str = "all",
        limit: int = 5,
    ) -> SearchSuggestionResponse:
        """获取搜索建议"""
        if len(query) < 2:
            return SearchSuggestionResponse(data=[])

        suggestions = await self.repository.get_suggestions(
            query=query,
            search_type=search_type,
            limit=limit,
        )

        return SearchSuggestionResponse(
            data=[SearchSuggestion(text=text, type=s_type, score=score) for text, s_type, score in suggestions]
        )

    async def get_history(
        self,
        user_id: int,
        pagination: PaginationParams,
    ) -> dict:
        """获取搜索历史"""
        histories, total = await self.repository.get_search_history(
            user_id=user_id,
            skip=pagination.skip,
            limit=pagination.limit,
        )

        total_pages = (total + pagination.page_size - 1) // pagination.page_size

        return {
            "data": [
                SearchHistoryRead(
                    id=h.id,
                    query=h.query,
                    search_type=h.search_type,
                    result_count=h.result_count,
                    created_at=h.created_at,
                )
                for h in histories
            ],
            "total": total,
            "page": pagination.page,
            "page_size": pagination.page_size,
            "total_pages": total_pages,
        }

    async def delete_history(
        self,
        user_id: int,
        history_id: int,
    ) -> bool:
        """删除搜索历史"""
        return await self.repository.delete_search_history(user_id, history_id)

    async def clear_history(
        self,
        user_id: int,
    ) -> int:
        """清空搜索历史"""
        return await self.repository.clear_search_history(user_id)
