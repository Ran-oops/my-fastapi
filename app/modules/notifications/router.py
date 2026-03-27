from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.common.schemas import DataResponse
from app.db.session import get_user_session as get_session
from app.modules.notifications import service as notification_service
from app.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationResponse,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
)
from app.modules.users.models import User


router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    page: int = 1,
    page_size: int = 20,
    is_read: bool | None = None,
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取我的通知列表"""
    skip = (page - 1) * page_size
    notifications = await notification_service.get_notifications(
        session, current_user.id, skip, page_size, is_read, status
    )
    total = await notification_service.get_notification_count(session, current_user.id, is_read, status)
    return NotificationListResponse(
        data=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{notification_id}", response_model=DataResponse[NotificationResponse])
async def get_notification(
    notification_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取通知详情"""
    notification = await notification_service.get_notification_by_id(session, notification_id, current_user.id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return DataResponse(data=NotificationResponse.model_validate(notification))


@router.put("/{notification_id}/read", response_model=DataResponse[NotificationResponse])
async def mark_read(
    notification_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """标记单条已读"""
    notification = await notification_service.mark_notification_read(session, notification_id, current_user.id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return DataResponse(data=NotificationResponse.model_validate(notification))


@router.put("/read-all", response_model=DataResponse[dict])
async def mark_all_read(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """标记全部已读"""
    count = await notification_service.mark_all_read(session, current_user.id)
    return DataResponse(data={"marked_count": count})


@router.get("/templates/", response_model=DataResponse[list[NotificationTemplateResponse]])
async def list_templates(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_superuser),
):
    """获取模板列表（管理员）"""
    templates = await notification_service.get_templates(session)
    return DataResponse(data=[NotificationTemplateResponse.model_validate(t) for t in templates])


@router.post(
    "/templates/", response_model=DataResponse[NotificationTemplateResponse], status_code=status.HTTP_201_CREATED
)
async def create_template(
    data: NotificationTemplateCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_superuser),
):
    """创建模板（管理员）"""
    template = await notification_service.create_template(session, data)
    return DataResponse(data=NotificationTemplateResponse.model_validate(template))


@router.put("/templates/{template_id}", response_model=DataResponse[NotificationTemplateResponse])
async def update_template(
    template_id: int,
    data: NotificationTemplateUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_superuser),
):
    """更新模板（管理员）"""
    try:
        template = await notification_service.update_template(session, template_id, data)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return DataResponse(data=NotificationTemplateResponse.model_validate(template))


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_superuser),
):
    """删除模板（管理员）"""
    try:
        await notification_service.delete_template(session, template_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
