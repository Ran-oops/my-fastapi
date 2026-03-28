from __future__ import annotations

import asyncio
from datetime import datetime

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
    order_status: str | None = Query(None, alias="status", description="订单状态过滤"),
    user_id: int | None = Query(None, description="用户ID过滤"),
    date_from: str | None = Query(None, description="开始日期 (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="结束日期 (YYYY-MM-DD)"),
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
            filters["category"] = category
        if price_min is not None:
            filters["price_min"] = price_min
        if price_max is not None:
            filters["price_max"] = price_max
        if is_active is not None:
            filters["is_active"] = is_active
        if order_status:
            filters["status"] = order_status
        if user_id is not None:
            filters["user_id"] = user_id
        if date_from:
            try:
                filters["date_from"] = datetime.fromisoformat(date_from)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="date_from格式无效，请使用YYYY-MM-DD格式"
                )
        if date_to:
            try:
                filters["date_to"] = datetime.fromisoformat(date_to)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="date_to格式无效，请使用YYYY-MM-DD格式"
                )

        # 添加排序参数
        filters["sort_by"] = sort_by
        filters["sort_order"] = sort_order

        # 使用asyncio.wait_for实现超时保护
        try:
            return await asyncio.wait_for(
                service.search(
                    query=q,
                    search_type=type,
                    user_id=current_user.id,
                    pagination=pagination,
                    filters=filters if filters else None,
                ),
                timeout=3.0,  # 3秒超时
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="搜索请求超时，请稍后重试")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
    return await service.suggest(query=q, search_type=type, limit=limit)


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
    return await service.get_history(user_id=current_user.id, pagination=pagination)


@router.delete("/history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(
    history_id: int,
    session: AsyncSession = Depends(get_user_session),
    current_user: User = Depends(get_current_user),
):
    """删除搜索历史"""
    service = SearchService(session)
    deleted = await service.delete_history(user_id=current_user.id, history_id=history_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="搜索历史不存在")
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
