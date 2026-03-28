from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_active_superuser
from app.db.session import get_user_session as get_session
from app.common.schemas import DataResponse
from app.modules.users.models import User
from app.tasks.dispatcher import dispatch
from app.modules.exports.tasks import export_order_data, export_product_data, export_audit_logs

router = APIRouter()


@router.post("/orders/", response_model=DataResponse[dict], status_code=status.HTTP_202_ACCEPTED)
async def export_orders(
    format: str = "csv",
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 1000,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Export order data (admin only)"""
    filters = {
        "status": status,
        "user_id": user_id,
        "date_from": date_from,
        "date_to": date_to,
        "limit": limit,
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    result = dispatch(export_order_data, filters, format)
    return DataResponse(data={"task_id": result.id, "status": "pending"})


@router.post("/products/", response_model=DataResponse[dict], status_code=status.HTTP_202_ACCEPTED)
async def export_products(
    format: str = "csv",
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 1000,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Export product data (admin only)"""
    filters = {
        "category": category,
        "is_active": is_active,
        "limit": limit,
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    result = dispatch(export_product_data, filters, format)
    return DataResponse(data={"task_id": result.id, "status": "pending"})


@router.post("/audit/", response_model=DataResponse[dict], status_code=status.HTTP_202_ACCEPTED)
async def export_audit(
    format: str = "csv",
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 1000,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_superuser),
):
    """Export audit logs (superuser only)"""
    filters = {
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "date_from": date_from,
        "date_to": date_to,
        "limit": limit,
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    result = dispatch(export_audit_logs, filters, format)
    return DataResponse(data={"task_id": result.id, "status": "pending"})
