
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.common.schemas import DataResponse
from app.db.session import get_user_session as get_session
from app.modules.exports.tasks import export_audit_logs, export_order_data, export_product_data
from app.modules.users.models import User
from app.tasks.celery_app import celery_app
from app.tasks.dispatcher import dispatch


router = APIRouter()


VALID_FORMATS = ["csv", "json", "excel"]


@router.get("/status/{task_id}", response_model=DataResponse[dict])
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get export task status"""
    result = celery_app.AsyncResult(task_id)
    response = {
        "task_id": task_id,
        "status": result.state,
    }
    if result.state == "SUCCESS":
        response["result"] = result.result
    elif result.state == "FAILURE":
        response["error"] = str(result.info)
    return DataResponse(data=response)


@router.post("/orders/", response_model=DataResponse[dict], status_code=status.HTTP_202_ACCEPTED)
async def export_orders(
    format: str = "csv",
    order_status: str | None = None,
    user_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 1000,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Export order data (admin only). Formats: csv, json, excel"""
    if format not in VALID_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format. Supported formats: {VALID_FORMATS}",
        )
    filters = {
        "status": order_status,
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
    category: str | None = None,
    is_active: bool | None = None,
    limit: int = 1000,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Export product data (admin only). Formats: csv, json, excel"""
    if format not in VALID_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format. Supported formats: {VALID_FORMATS}",
        )
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
    user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 1000,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_superuser),
):
    """Export audit logs (superuser only). Formats: csv, json, excel"""
    if format not in VALID_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format. Supported formats: {VALID_FORMATS}",
        )
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
