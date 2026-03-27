# Notifications Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现事件驱动的通知系统，支持站内信和邮件渠道，可扩展架构。

**Architecture:** 采用发布-订阅模式，通过 EventBus 解耦业务模块和通知系统。NotificationHandler 处理事件并调用各渠道发送通知。

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic V2, pytest

**Spec:** `docs/superpowers/specs/2026-03-27-notifications-module-design.md`

---

## File Structure

```
app/
├── core/
│   ├── eventbus.py          # 新增：事件总线
│   └── events.py            # 新增：事件类型定义
└── modules/
    └── notifications/
        ├── __init__.py      # 修改：导出
        ├── models.py        # 新增：数据模型
        ├── schemas.py       # 新增：Pydantic schemas
        ├── repository.py    # 新增：数据访问层
        ├── service.py       # 重写：业务逻辑层
        ├── router.py        # 新增：API 路由
        ├── channels.py      # 新增：通知渠道
        └── handlers.py      # 新增：事件处理器

tests/
└── modules/
    └── notifications/
        ├── __init__.py      # 新增
        ├── conftest.py      # 新增：测试 fixtures
        ├── test_eventbus.py # 新增：EventBus 测试
        ├── test_channels.py # 新增：渠道测试
        ├── test_service.py  # 新增：Service 测试
        └── test_api.py      # 新增：API 测试

alembic/
└── versions/
    └── 2026_03_27_0000-001_add_notifications.py  # 新增：数据库迁移
```

---

## Task 1: EventBus 核心实现

**Files:**
- Create: `app/core/eventbus.py`
- Create: `app/core/events.py`
- Create: `tests/modules/notifications/__init__.py`
- Create: `tests/modules/notifications/test_eventbus.py`

- [ ] **Step 1: 创建事件类型定义文件**

Create `app/core/events.py`:

```python
# 订单事件
ORDER_CREATED = "order.created"
ORDER_CONFIRMED = "order.confirmed"
ORDER_SHIPPED = "order.shipped"
ORDER_COMPLETED = "order.completed"
ORDER_CANCELLED = "order.cancelled"

# 用户事件
USER_REGISTERED = "user.registered"
USER_PASSWORD_RESET = "user.password_reset"

# 任务事件
TASK_COMPLETED = "task.completed"
TASK_FAILED = "task.failed"
```

- [ ] **Step 2: 创建 EventBus 实现**

Create `app/core/eventbus.py`:

```python
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Callable


@dataclass
class Event:
    """领域事件"""
    event_type: str
    data: dict
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class EventBus:
    """事件总线 - 发布/订阅模式"""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """订阅事件"""
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

    def publish(self, event: Event) -> None:
        """发布事件"""
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            handler(event)

    def clear(self) -> None:
        """清空所有订阅（测试用）"""
        self._subscribers.clear()


eventbus = EventBus()
```

- [ ] **Step 3: 创建测试文件**

Create `tests/modules/notifications/__init__.py` (empty file).

Create `tests/modules/notifications/test_eventbus.py`:

```python
import pytest

from app.core.eventbus import EventBus, Event


@pytest.mark.asyncio
class TestEventBus:
    async def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []

        def handler(event: Event):
            received.append(event)

        bus.subscribe("test.event", handler)
        bus.publish(Event(event_type="test.event", data={"key": "value"}))

        assert len(received) == 1
        assert received[0].event_type == "test.event"
        assert received[0].data == {"key": "value"}

    async def test_multiple_handlers(self):
        bus = EventBus()
        results = []

        bus.subscribe("test.event", lambda e: results.append("handler1"))
        bus.subscribe("test.event", lambda e: results.append("handler2"))
        bus.publish(Event(event_type="test.event", data={}))

        assert results == ["handler1", "handler2"]

    async def test_unsubscribe(self):
        bus = EventBus()
        received = []

        def handler(event: Event):
            received.append(event)

        bus.subscribe("test.event", handler)
        bus.unsubscribe("test.event", handler)
        bus.publish(Event(event_type="test.event", data={}))

        assert len(received) == 0

    async def test_clear(self):
        bus = EventBus()
        received = []

        bus.subscribe("test.event", lambda e: received.append(e))
        bus.clear()
        bus.publish(Event(event_type="test.event", data={}))

        assert len(received) == 0

    async def test_event_has_timestamp(self):
        event = Event(event_type="test.event", data={})
        assert event.timestamp is not None
```

- [ ] **Step 4: 运行测试**

Run: `uv run pytest tests/modules/notifications/test_eventbus.py -v`

Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/eventbus.py app/core/events.py tests/modules/notifications/
git commit -m "feat(core): add EventBus for event-driven architecture"
```

---

## Task 2: Notification 数据模型

**Files:**
- Create: `app/modules/notifications/models.py`
- Create: `alembic/versions/2026_03_27_0000-001_add_notifications.py`

- [ ] **Step 1: 创建数据模型**

Create `app/modules/notifications/models.py`:

```python
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
```

- [ ] **Step 2: 创建数据库迁移**

Create `alembic/versions/2026_03_27_0000-001_add_notifications.py`:

```python
"""add notifications tables

Revision ID: 2026_03_27_0000-001
Revises: 
Create Date: 2026-03-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2026_03_27_0000-001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notification_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('subject', sa.String(length=200), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_notification_templates_name', 'notification_templates', ['name'])

    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('template_name', sa.String(length=100), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, default='pending'),
        sa.Column('subject', sa.String(length=200), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=True, default=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_status', 'notifications', ['status'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])

    op.create_table(
        'notification_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('sms_enabled', sa.Boolean(), nullable=True, default=False),
        sa.Column('in_app_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_preferences_user_id', 'notification_preferences', ['user_id'])


def downgrade() -> None:
    op.drop_table('notification_preferences')
    op.drop_table('notifications')
    op.drop_table('notification_templates')
```

- [ ] **Step 3: 运行迁移**

Run: `uv run alembic upgrade head`

Expected: Migration succeeds

- [ ] **Step 4: Commit**

```bash
git add app/modules/notifications/models.py alembic/versions/2026_03_27_0000-001_add_notifications.py
git commit -m "feat(notifications): add data models and migration"
```

---

## Task 3: Notification Schemas

**Files:**
- Create: `app/modules/notifications/schemas.py`

- [ ] **Step 1: 创建 Pydantic schemas**

Create `app/modules/notifications/schemas.py`:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/notifications/schemas.py
git commit -m "feat(notifications): add Pydantic schemas"
```

---

## Task 4: Repository 层

**Files:**
- Create: `app/modules/notifications/repository.py`

- [ ] **Step 1: 创建 Repository**

Create `app/modules/notifications/repository.py`:

```python
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import BaseRepository
from app.modules.notifications.models import Notification, NotificationTemplate


class NotificationRepository(BaseRepository[Notification]):
    """通知仓库"""

    def __init__(self):
        super().__init__(Notification)

    async def get_by_user(
        self,
        session: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        is_read: Optional[bool] = None,
        status: Optional[str] = None,
    ) -> list[Notification]:
        """获取用户通知列表"""
        conditions = [Notification.user_id == user_id]
        if is_read is not None:
            conditions.append(Notification.is_read == is_read)
        if status is not None:
            conditions.append(Notification.status == status)

        stmt = (
            select(Notification)
            .where(and_(*conditions))
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        session: AsyncSession,
        user_id: int,
        is_read: Optional[bool] = None,
        status: Optional[str] = None,
    ) -> int:
        """统计用户通知数量"""
        conditions = [Notification.user_id == user_id]
        if is_read is not None:
            conditions.append(Notification.is_read == is_read)
        if status is not None:
            conditions.append(Notification.status == status)

        stmt = select(Notification.id).where(and_(*conditions))
        result = await session.execute(stmt)
        return len(list(result.all()))

    async def mark_read(
        self, session: AsyncSession, notification_id: int, user_id: int
    ) -> Optional[Notification]:
        """标记单条已读"""
        stmt = select(Notification).where(
            and_(Notification.id == notification_id, Notification.user_id == user_id)
        )
        result = await session.execute(stmt)
        notification = result.scalar_one_or_none()
        if notification:
            notification.is_read = True
            await session.commit()
            await session.refresh(notification)
        return notification

    async def mark_all_read(self, session: AsyncSession, user_id: int) -> int:
        """标记全部已读"""
        stmt = select(Notification).where(
            and_(Notification.user_id == user_id, Notification.is_read == False)
        )
        result = await session.execute(stmt)
        notifications = list(result.scalars().all())
        count = 0
        for notification in notifications:
            notification.is_read = True
            count += 1
        await session.commit()
        return count


class NotificationTemplateRepository(BaseRepository[NotificationTemplate]):
    """通知模板仓库"""

    def __init__(self):
        super().__init__(NotificationTemplate)

    async def get_by_name(
        self, session: AsyncSession, name: str, channel: str
    ) -> Optional[NotificationTemplate]:
        """根据名称和渠道获取模板"""
        stmt = select(NotificationTemplate).where(
            and_(
                NotificationTemplate.name == name,
                NotificationTemplate.channel == channel,
                NotificationTemplate.is_active == True,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


notification_repo = NotificationRepository()
template_repo = NotificationTemplateRepository()
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/notifications/repository.py
git commit -m "feat(notifications): add repository layer"
```

---

## Task 5: 通知渠道实现

**Files:**
- Create: `app/modules/notifications/channels.py`
- Create: `tests/modules/notifications/test_channels.py`

- [ ] **Step 1: 创建通知渠道抽象和实现**

Create `app/modules/notifications/channels.py`:

```python
from abc import ABC, abstractmethod
from typing import Optional


class NotificationChannel(ABC):
    """通知渠道抽象基类"""

    @abstractmethod
    async def send(
        self, user_id: int, subject: Optional[str], body: str
    ) -> tuple[bool, Optional[str]]:
        """
        发送通知
        
        Returns:
            (success, error_message)
        """
        pass


class InAppChannel(NotificationChannel):
    """站内信渠道 - 仅记录到数据库"""

    async def send(
        self, user_id: int, subject: Optional[str], body: str
    ) -> tuple[bool, Optional[str]]:
        return True, None


class EmailChannel(NotificationChannel):
    """邮件渠道 - 占位实现"""

    async def send(
        self, user_id: int, subject: Optional[str], body: str
    ) -> tuple[bool, Optional[str]]:
        print(f"[Email] user_id={user_id}, subject={subject}")
        return True, None


class SmsChannel(NotificationChannel):
    """短信渠道 - 预留"""

    async def send(
        self, user_id: int, subject: Optional[str], body: str
    ) -> tuple[bool, Optional[str]]:
        return False, "SMS channel not implemented"


CHANNEL_REGISTRY: dict[str, NotificationChannel] = {
    "in_app": InAppChannel(),
    "email": EmailChannel(),
    "sms": SmsChannel(),
}
```

- [ ] **Step 2: 创建测试**

Create `tests/modules/notifications/test_channels.py`:

```python
import pytest

from app.modules.notifications.channels import (
    InAppChannel,
    EmailChannel,
    SmsChannel,
    CHANNEL_REGISTRY,
)


@pytest.mark.asyncio
class TestChannels:
    async def test_in_app_channel_send(self):
        channel = InAppChannel()
        success, error = await channel.send(1, "Test Subject", "Test Body")
        assert success is True
        assert error is None

    async def test_email_channel_send(self):
        channel = EmailChannel()
        success, error = await channel.send(1, "Test Subject", "Test Body")
        assert success is True
        assert error is None

    async def test_sms_channel_not_implemented(self):
        channel = SmsChannel()
        success, error = await channel.send(1, "Test", "Test")
        assert success is False
        assert "not implemented" in error

    async def test_channel_registry_contains_all_channels(self):
        assert "in_app" in CHANNEL_REGISTRY
        assert "email" in CHANNEL_REGISTRY
        assert "sms" in CHANNEL_REGISTRY

    async def test_channel_registry_returns_correct_types(self):
        assert isinstance(CHANNEL_REGISTRY["in_app"], InAppChannel)
        assert isinstance(CHANNEL_REGISTRY["email"], EmailChannel)
        assert isinstance(CHANNEL_REGISTRY["sms"], SmsChannel)
```

- [ ] **Step 3: 运行测试**

Run: `uv run pytest tests/modules/notifications/test_channels.py -v`

Expected: All 5 tests PASS

- [ ] **Step 4: Commit**

```bash
git add app/modules/notifications/channels.py tests/modules/notifications/test_channels.py
git commit -m "feat(notifications): add notification channels"
```

---

## Task 6: 事件处理器

**Files:**
- Create: `app/modules/notifications/handlers.py`

- [ ] **Step 1: 创建事件处理器**

Create `app/modules/notifications/handlers.py`:

```python
import logging
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.eventbus import Event
from app.modules.notifications.channels import CHANNEL_REGISTRY
from app.modules.notifications.models import Notification, NotificationTemplate
from app.modules.notifications.repository import template_repo

logger = logging.getLogger(__name__)


class NotificationHandler:
    """事件驱动的通知处理器"""

    async def handle_event(
        self, session: AsyncSession, event: Event
    ) -> list[Notification]:
        """处理事件，发送通知到所有渠道"""
        notifications = []
        user_id = event.data.get("user_id")
        if not user_id:
            logger.warning(f"Event {event.event_type} missing user_id")
            return notifications

        for channel_name, channel in CHANNEL_REGISTRY.items():
            notification = await self._send_to_channel(
                session, event, channel_name, channel, user_id
            )
            if notification:
                notifications.append(notification)

        return notifications

    async def _send_to_channel(
        self,
        session: AsyncSession,
        event: Event,
        channel_name: str,
        channel,
        user_id: int,
    ) -> Optional[Notification]:
        """发送到单个渠道"""
        template = await template_repo.get_by_name(session, event.event_type, channel_name)
        if not template:
            logger.debug(f"No template for {event.event_type}/{channel_name}")
            return None

        if not template.is_active:
            return None

        subject = self._render(template.subject, event.data) if template.subject else None
        body = self._render(template.body, event.data)

        notification = Notification(
            user_id=user_id,
            template_name=event.event_type,
            channel=channel_name,
            status="pending",
            subject=subject,
            body=body,
        )
        session.add(notification)
        await session.flush()

        try:
            success, error = await channel.send(user_id, subject, body)
            notification.status = "sent" if success else "failed"
            notification.sent_at = datetime.now(UTC) if success else None
            notification.error_message = error
        except Exception as e:
            logger.exception(f"Failed to send notification via {channel_name}")
            notification.status = "failed"
            notification.error_message = str(e)

        await session.commit()
        await session.refresh(notification)
        return notification

    def _render(self, template: Optional[str], context: dict) -> str:
        """简单模板渲染"""
        if not template:
            return ""
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result


notification_handler = NotificationHandler()
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/notifications/handlers.py
git commit -m "feat(notifications): add event handler"
```

---

## Task 7: Service 层

**Files:**
- Rewrite: `app/modules/notifications/service.py`
- Create: `tests/modules/notifications/conftest.py`
- Create: `tests/modules/notifications/test_service.py`

- [ ] **Step 1: 重写 Service**

Rewrite `app/modules/notifications/service.py`:

```python
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.eventbus import eventbus, Event
from app.modules.notifications.handlers import notification_handler
from app.modules.notifications.models import Notification, NotificationTemplate
from app.modules.notifications.repository import notification_repo, template_repo
from app.modules.notifications.schemas import (
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
    NotificationMarkRead,
)


async def get_notifications(
    session: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    is_read: Optional[bool] = None,
    status: Optional[str] = None,
) -> list[Notification]:
    """获取用户通知列表"""
    return await notification_repo.get_by_user(
        session, user_id, skip, limit, is_read, status
    )


async def get_notification_count(
    session: AsyncSession,
    user_id: int,
    is_read: Optional[bool] = None,
    status: Optional[str] = None,
) -> int:
    """获取用户通知数量"""
    return await notification_repo.count_by_user(session, user_id, is_read, status)


async def get_notification_by_id(
    session: AsyncSession, notification_id: int, user_id: int
) -> Optional[Notification]:
    """获取单条通知"""
    return await notification_repo.get(session, id=notification_id)


async def mark_notification_read(
    session: AsyncSession, notification_id: int, user_id: int
) -> Optional[Notification]:
    """标记单条已读"""
    return await notification_repo.mark_read(session, notification_id, user_id)


async def mark_all_read(session: AsyncSession, user_id: int) -> int:
    """标记全部已读"""
    return await notification_repo.mark_all_read(session, user_id)


async def create_template(
    session: AsyncSession, data: NotificationTemplateCreate
) -> NotificationTemplate:
    """创建通知模板"""
    return await template_repo.create(session, data=data)


async def update_template(
    session: AsyncSession, template_id: int, data: NotificationTemplateUpdate
) -> NotificationTemplate:
    """更新通知模板"""
    template = await template_repo.get(session, id=template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")
    return await template_repo.update(session, instance=template, data=data)


async def delete_template(session: AsyncSession, template_id: int) -> NotificationTemplate:
    """删除通知模板"""
    return await template_repo.delete(session, id=template_id)


async def get_templates(
    session: AsyncSession, skip: int = 0, limit: int = 100
) -> list[NotificationTemplate]:
    """获取模板列表"""
    return await template_repo.get_multi(session, skip=skip, limit=limit)


async def publish_event(event_type: str, data: dict) -> None:
    """发布事件（供业务模块调用）"""
    event = Event(event_type=event_type, data=data)
    eventbus.publish(event)
```

- [ ] **Step 2: 创建测试 fixtures**

Create `tests/modules/notifications/conftest.py`:

```python
import pytest_asyncio

from app.core.eventbus import eventbus
from app.modules.notifications.models import NotificationTemplate
from app.modules.notifications.schemas import NotificationTemplateCreate


@pytest_asyncio.fixture
async def test_template(session):
    """创建测试模板"""
    template = NotificationTemplate(
        name="test.event",
        channel="in_app",
        subject="Test Subject",
        body="Hello {{user_id}}, message: {{message}}",
        is_active=True,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@pytest_asyncio.fixture
async def test_email_template(session):
    """创建邮件测试模板"""
    template = NotificationTemplate(
        name="test.event",
        channel="email",
        subject="Email for {{user_id}}",
        body="Email body: {{message}}",
        is_active=True,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@pytest_asyncio.fixture(autouse=True)
def clear_eventbus():
    """每个测试前后清空事件总线"""
    eventbus.clear()
    yield
    eventbus.clear()
```

- [ ] **Step 3: 创建 Service 测试**

Create `tests/modules/notifications/test_service.py`:

```python
import pytest

from app.modules.notifications import service as notification_service
from app.modules.notifications.schemas import NotificationTemplateCreate


@pytest.mark.asyncio
class TestNotificationService:
    async def test_create_template(self, session):
        data = NotificationTemplateCreate(
            name="order.confirmed",
            channel="in_app",
            subject="Order Confirmed",
            body="Your order #{{order_id}} is confirmed",
        )
        template = await notification_service.create_template(session, data)
        assert template.id is not None
        assert template.name == "order.confirmed"
        assert template.channel == "in_app"

    async def test_get_templates(self, session, test_template):
        templates = await notification_service.get_templates(session)
        assert len(templates) >= 1
        assert any(t.name == "test.event" for t in templates)

    async def test_create_and_get_notification(self, session, test_template):
        from app.modules.notifications.models import Notification

        notification = Notification(
            user_id=1,
            template_name="test.event",
            channel="in_app",
            status="sent",
            subject="Test",
            body="Test body",
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)

        notifications = await notification_service.get_notifications(session, user_id=1)
        assert len(notifications) >= 1
        assert notifications[0].template_name == "test.event"
```

- [ ] **Step 4: 运行测试**

Run: `uv run pytest tests/modules/notifications/test_service.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/modules/notifications/service.py tests/modules/notifications/conftest.py tests/modules/notifications/test_service.py
git commit -m "feat(notifications): add service layer with tests"
```

---

## Task 8: API 路由

**Files:**
- Create: `app/modules/notifications/router.py`
- Create: `tests/modules/notifications/test_api.py`

- [ ] **Step 1: 创建 API 路由**

Create `app/modules/notifications/router.py`:

```python
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_superuser, get_session
from app.common.schemas import ResponseSchema
from app.modules.notifications import service as notification_service
from app.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationResponse,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
    NotificationMarkRead,
)
from app.modules.users.models import User

router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    page: int = 1,
    page_size: int = 20,
    is_read: Optional[bool] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取我的通知列表"""
    skip = (page - 1) * page_size
    notifications = await notification_service.get_notifications(
        session, current_user.id, skip, page_size, is_read, status
    )
    total = await notification_service.get_notification_count(
        session, current_user.id, is_read, status
    )
    return NotificationListResponse(
        data=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{notification_id}", response_model=ResponseSchema[NotificationResponse])
async def get_notification(
    notification_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取通知详情"""
    notification = await notification_service.get_notification_by_id(
        session, notification_id, current_user.id
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return ResponseSchema(data=NotificationResponse.model_validate(notification))


@router.put("/{notification_id}/read", response_model=ResponseSchema[NotificationResponse])
async def mark_read(
    notification_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """标记单条已读"""
    notification = await notification_service.mark_notification_read(
        session, notification_id, current_user.id
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return ResponseSchema(data=NotificationResponse.model_validate(notification))


@router.put("/read-all", response_model=ResponseSchema[dict])
async def mark_all_read(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """标记全部已读"""
    count = await notification_service.mark_all_read(session, current_user.id)
    return ResponseSchema(data={"marked_count": count})


@router.get("/templates/", response_model=ResponseSchema[list[NotificationTemplateResponse]])
async def list_templates(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_superuser),
):
    """获取模板列表（管理员）"""
    templates = await notification_service.get_templates(session)
    return ResponseSchema(
        data=[NotificationTemplateResponse.model_validate(t) for t in templates]
    )


@router.post("/templates/", response_model=ResponseSchema[NotificationTemplateResponse], status_code=status.HTTP_201_CREATED)
async def create_template(
    data: NotificationTemplateCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_superuser),
):
    """创建模板（管理员）"""
    template = await notification_service.create_template(session, data)
    return ResponseSchema(data=NotificationTemplateResponse.model_validate(template))


@router.put("/templates/{template_id}", response_model=ResponseSchema[NotificationTemplateResponse])
async def update_template(
    template_id: int,
    data: NotificationTemplateUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_superuser),
):
    """更新模板（管理员）"""
    try:
        template = await notification_service.update_template(session, template_id, data)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return ResponseSchema(data=NotificationTemplateResponse.model_validate(template))


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_superuser),
):
    """删除模板（管理员）"""
    try:
        await notification_service.delete_template(session, template_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
```

- [ ] **Step 2: 注册路由**

Modify `app/api/v1/__init__.py` to add:

```python
from app.modules.notifications.router import router as notifications_router
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
```

- [ ] **Step 3: 创建 API 测试**

Create `tests/modules/notifications/test_api.py`:

```python
import pytest
from fastapi import status


@pytest.mark.asyncio
class TestNotificationAPI:
    async def test_list_notifications_unauthorized(self, client):
        response = await client.get("/api/v1/notifications/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_list_notifications_success(self, client, user_headers):
        response = await client.get("/api/v1/notifications/", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data

    async def test_list_templates_forbidden(self, client, user_headers):
        response = await client.get("/api/v1/notifications/templates/", headers=user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_list_templates_admin(self, client, superuser_headers):
        response = await client.get("/api/v1/notifications/templates/", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
```

- [ ] **Step 4: 运行测试**

Run: `uv run pytest tests/modules/notifications/test_api.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/modules/notifications/router.py app/api/v1/__init__.py tests/modules/notifications/test_api.py
git commit -m "feat(notifications): add API routes with tests"
```

---

## Task 9: 订单模块集成

**Files:**
- Modify: `app/modules/orders/service.py`

- [ ] **Step 1: 集成事件发布**

Modify `app/modules/orders/service.py`:

Add imports at top:
```python
from app.core.eventbus import eventbus, Event
from app.core.events import ORDER_CONFIRMED, ORDER_SHIPPED, ORDER_CANCELLED
```

Modify `update_order_status` function, add after `await session.refresh(order)`:

```python
# 发布事件
from app.core.eventbus import eventbus, Event
from app.core.events import ORDER_CONFIRMED, ORDER_SHIPPED, ORDER_CANCELLED

if data.status:
    event_type = None
    if data.status == OrderStatus.CONFIRMED:
        event_type = ORDER_CONFIRMED
    elif data.status == OrderStatus.SHIPPED:
        event_type = ORDER_SHIPPED
    elif data.status == OrderStatus.CANCELLED:
        event_type = ORDER_CANCELLED
    
    if event_type:
        eventbus.publish(Event(
            event_type=event_type,
            data={"order_id": order_id, "user_id": order.user_id}
        ))
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/orders/service.py
git commit -m "feat(orders): integrate with notification events"
```

---

## Task 10: 订阅事件处理器

**Files:**
- Modify: `app/modules/notifications/__init__.py`
- Modify: `app/main.py`

- [ ] **Step 1: 导出并注册订阅**

Modify `app/modules/notifications/__init__.py`:

```python
from app.modules.notifications.service import (
    get_notifications,
    get_notification_count,
    mark_notification_read,
    mark_all_read,
    create_template,
    update_template,
    delete_template,
    get_templates,
    publish_event,
)
from app.modules.notifications.handlers import notification_handler

__all__ = [
    "get_notifications",
    "get_notification_count",
    "mark_notification_read",
    "mark_all_read",
    "create_template",
    "update_template",
    "delete_template",
    "get_templates",
    "publish_event",
    "notification_handler",
]
```

- [ ] **Step 2: 在启动时注册订阅**

Modify `app/main.py`:

Add imports:
```python
from app.core.eventbus import eventbus
from app.modules.notifications.handlers import notification_handler
from app.core.events import (
    ORDER_CONFIRMED, ORDER_SHIPPED, ORDER_CANCELLED,
    USER_REGISTERED, USER_PASSWORD_RESET,
    TASK_COMPLETED, TASK_FAILED,
)
```

Add in `lifespan` context manager after `logger.info("Application starting up...")`:

```python
# 注册通知事件处理器
async def handle_notification_event(event):
    from app.db.session import UserSessionFactory
    async with UserSessionFactory() as session:
        await notification_handler.handle_event(session, event)

for event_type in [ORDER_CONFIRMED, ORDER_SHIPPED, ORDER_CANCELLED, USER_REGISTERED, USER_PASSWORD_RESET, TASK_COMPLETED, TASK_FAILED]:
    eventbus.subscribe(event_type, lambda e: asyncio.create_task(handle_notification_event(e)))

import asyncio
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/notifications/__init__.py app/main.py
git commit -m "feat: register notification event handlers on startup"
```

---

## Task 11: 最终验证

- [ ] **Step 1: 运行全部测试**

Run: `uv run pytest tests -v --tb=short`

Expected: All tests PASS

- [ ] **Step 2: 运行代码检查**

Run: `uv run ruff check app tests`

Expected: All checks passed

- [ ] **Step 3: 运行格式化**

Run: `uv run ruff format app tests`

Expected: Files formatted

- [ ] **Step 4: 最终提交**

```bash
git add -A
git commit -m "feat(notifications): complete event-driven notification system"
```

---

## Summary

**Tasks:** 11
**Files Created:** 14
**Files Modified:** 4
**Expected Result:** 
- EventBus 可发布和订阅事件
- 订单状态变更触发通知
- 通知记录存储到数据库
- 用户可查询通知列表
- 用户可标记通知已读
- 管理员可管理通知模板
- 所有测试通过
