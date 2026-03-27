from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NotificationTemplateCreate(BaseModel):
    """创建通知模板"""

    name: str = Field(..., max_length=100)
    channel: str = Field(..., max_length=20)
    subject: Optional[str] = Field(None, max_length=200)
    body: str
    is_active: bool = True


class NotificationTemplateUpdate(BaseModel):
    """更新通知模板"""

    name: Optional[str] = Field(None, max_length=100)
    channel: Optional[str] = Field(None, max_length=20)
    subject: Optional[str] = Field(None, max_length=200)
    body: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationTemplateResponse(BaseModel):
    """通知模板响应"""

    id: int
    name: str
    channel: str
    subject: Optional[str]
    body: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    """通知响应"""

    id: int
    user_id: int
    template_name: str
    channel: str
    status: str
    subject: Optional[str]
    body: str
    is_read: bool
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """通知列表响应"""

    data: list[NotificationResponse]
    total: int
    page: int
    page_size: int


class NotificationMarkRead(BaseModel):
    """标记已读请求"""

    notification_ids: list[int]
