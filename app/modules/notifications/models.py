from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import mapped_column

from app.db.base import UserBase


class NotificationTemplate(UserBase):
    """通知模板"""

    __tablename__ = "notification_templates"

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(100), unique=True, nullable=False, index=True)
    channel = mapped_column(String(20), nullable=False)
    subject = mapped_column(String(200), nullable=True)
    body = mapped_column(Text, nullable=False)
    is_active = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(UserBase):
    """通知记录"""

    __tablename__ = "notifications"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, nullable=False, index=True)
    template_name = mapped_column(String(100), nullable=False)
    channel = mapped_column(String(20), nullable=False)
    status = mapped_column(String(20), default="pending", index=True)
    subject = mapped_column(String(200), nullable=True)
    body = mapped_column(Text, nullable=False)
    is_read = mapped_column(Boolean, default=False, index=True)
    error_message = mapped_column(Text, nullable=True)
    sent_at = mapped_column(DateTime, nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)


class NotificationPreference(UserBase):
    """用户通知偏好（预留）"""

    __tablename__ = "notification_preferences"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, nullable=False, unique=True, index=True)
    email_enabled = mapped_column(Boolean, default=True)
    sms_enabled = mapped_column(Boolean, default=False)
    in_app_enabled = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
