from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


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
    created_at: datetime


class SearchHistoryResponse(BaseModel):
    """搜索历史响应"""

    data: list[SearchHistoryRead]
    total: int
    page: int
    page_size: int
    total_pages: int
