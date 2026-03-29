from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search.adapters.base import BaseSearchAdapter
from app.modules.search.adapters.postgresql import PostgreSQLSearchAdapter
from app.modules.search.adapters.sqlite import SQLiteSearchAdapter


def create_search_adapter(session: AsyncSession) -> BaseSearchAdapter:
    """根据数据库类型创建对应的搜索适配器"""
    dialect = session.bind.dialect.name

    if dialect == "postgresql":
        return PostgreSQLSearchAdapter(session)
    elif dialect == "sqlite":
        return SQLiteSearchAdapter(session)
    else:
        # 默认使用 SQLite 适配器(兼容性最好)
        return SQLiteSearchAdapter(session)


__all__ = [
    "BaseSearchAdapter",
    "PostgreSQLSearchAdapter",
    "SQLiteSearchAdapter",
    "create_search_adapter",
]
