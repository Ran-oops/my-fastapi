from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationTemplateCreate(BaseModel):
    """创建通知模板"""

    name: str = Field(..., max_length=100)
    channel: str = Field(..., max_length=20)
    subject: str | None = Field(None, max_length=200)
    body: str
    is_active: bool = True


class NotificationTemplateUpdate(BaseModel):
    """更新通知模板"""

    name: str | None = Field(None, max_length=100)
    channel: str | None = Field(None, max_length=20)
    subject: str | None = Field(None, max_length=200)
    body: str | None = None
    is_active: bool | None = None


class NotificationTemplateResponse(BaseModel):
    """通知模板响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    channel: str
    subject: str | None
    body: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None


class NotificationResponse(BaseModel):
    """通知响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    template_name: str
    channel: str
    status: str
    subject: str | None
    body: str
    is_read: bool
    sent_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    """通知列表响应"""

    data: list[NotificationResponse]
    total: int
    page: int
    page_size: int


class NotificationMarkRead(BaseModel):
    """标记已读请求"""

    notification_ids: list[int]
