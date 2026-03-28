from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search.adapters import BaseSearchAdapter, create_search_adapter
from app.modules.search.models import SearchHistory


class SearchRepository:
    """搜索数据访问层，使用适配器模式支持多数据库"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.adapter: BaseSearchAdapter = create_search_adapter(session)

    async def search_products(
        self, query: str, skip: int = 0, limit: int = 10, filters: dict | None = None
    ) -> tuple[list, int]:
        """搜索产品（委托给适配器）"""
        return await self.adapter.search_products(query, skip, limit, filters)

    async def search_orders(
        self, query: str, skip: int = 0, limit: int = 10, filters: dict | None = None
    ) -> tuple[list, int]:
        """搜索订单（委托给适配器）"""
        return await self.adapter.search_orders(query, skip, limit, filters)

    async def search_users(
        self, query: str, skip: int = 0, limit: int = 10, filters: dict | None = None
    ) -> tuple[list, int]:
        """搜索用户（委托给适配器）"""
        return await self.adapter.search_users(query, skip, limit, filters)

    async def get_suggestions(self, query: str, search_type: str, limit: int = 5) -> list[tuple[str, str, float]]:
        """获取搜索建议（委托给适配器）"""
        return await self.adapter.get_suggestions(query, search_type, limit)

    async def save_search_history(self, user_id: int, query: str, search_type: str, result_count: int) -> SearchHistory:
        """保存搜索历史（限制每个用户最多100条）"""
        # 保存新记录
        history = SearchHistory(user_id=user_id, query=query, search_type=search_type, result_count=result_count)
        self.session.add(history)
        await self.session.flush()  # 先flush获取ID

        # 检查并删除超过100条的旧记录
        count_stmt = select(func.count()).select_from(SearchHistory).where(SearchHistory.user_id == user_id)
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

    async def get_search_history(self, user_id: int, skip: int = 0, limit: int = 10) -> tuple[list[SearchHistory], int]:
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
        count_stmt = select(func.count()).select_from(SearchHistory).where(SearchHistory.user_id == user_id)
        total = await self.session.scalar(count_stmt)

        return histories, total or 0

    async def delete_search_history(self, user_id: int, history_id: int) -> bool:
        """删除搜索历史"""
        stmt = select(SearchHistory).where(SearchHistory.id == history_id).where(SearchHistory.user_id == user_id)
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
        count_stmt = select(func.count()).select_from(SearchHistory).where(SearchHistory.user_id == user_id)
        count = await self.session.scalar(count_stmt) or 0

        # 使用DELETE语句直接删除
        delete_stmt = delete(SearchHistory).where(SearchHistory.user_id == user_id)
        await self.session.execute(delete_stmt)
        await self.session.commit()

        return count
