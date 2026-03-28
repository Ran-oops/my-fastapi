from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class BaseSearchAdapter(ABC):
    """搜索适配器抽象基类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    @abstractmethod
    async def search_products(
        self, query: str, skip: int = 0, limit: int = 10, filters: dict | None = None
    ) -> tuple[list, int]:
        """搜索产品，返回 (结果列表, 总数)"""
        pass

    @abstractmethod
    async def search_orders(
        self, query: str, skip: int = 0, limit: int = 10, filters: dict | None = None
    ) -> tuple[list, int]:
        """搜索订单"""
        pass

    @abstractmethod
    async def search_users(
        self, query: str, skip: int = 0, limit: int = 10, filters: dict | None = None
    ) -> tuple[list, int]:
        """搜索用户"""
        pass

    @abstractmethod
    async def get_suggestions(self, query: str, search_type: str, limit: int = 5) -> list[tuple[str, str, float]]:
        """获取搜索建议，返回 [(文本, 类型, 相似度得分)]"""
        pass
