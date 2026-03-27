# Notifications Module Design - Event-Driven Architecture

## Overview

实现事件驱动的通知系统，支持站内信和邮件渠道，可扩展架构。

## Requirements

- **通知方式**：可扩展架构，先实现站内信和邮件
- **触发场景**：订单状态变更、用户账户事件、系统事件
- **持久化**：是，存储到数据库
- **模板管理**：数据库模板，支持动态修改
- **用户偏好**：先不实现，统一发送（预留表结构）

## Architecture

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      业务模块                           │
│  orders/users/tasks/...                                 │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   EventBus (事件总线)                   │
│  - publish(event)                                       │
│  - subscribe(event_type, handler)                       │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              NotificationHandler (事件处理器)           │
│  - 处理事件                                             │
│  - 查询模板                                             │
│  - 调用渠道                                             │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ InAppChannel │  │ EmailChannel │  │ SmsChannel   │
│   (站内信)   │  │   (邮件)     │  │   (短信)     │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 核心流程

1. 业务模块调用 `eventbus.publish(event)`
2. EventBus 通知所有订阅者
3. NotificationHandler 处理事件
4. 查询数据库获取模板
5. 调用各渠道发送通知
6. 存储通知记录

## Component Design

### 1. EventBus（事件总线）

**文件**：`app/core/eventbus.py`

```python
from typing import Callable
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Event:
    """领域事件基类"""
    event_type: str
    data: dict
    timestamp: datetime = field(default_factory=datetime.now)

class EventBus:
    """事件总线 - 发布/订阅模式"""
    
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
    
    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    def publish(self, event: Event):
        """发布事件"""
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            handler(event)

# 全局单例
eventbus = EventBus()
```

### 2. 事件类型定义

**文件**：`app/core/events.py`

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

### 3. 通知渠道接口

**文件**：`app/modules/notifications/channels.py`

```python
from abc import ABC, abstractmethod

class NotificationChannel(ABC):
    """通知渠道抽象基类"""
    
    @abstractmethod
    def send(self, user_id: int, subject: str, body: str) -> bool:
        """发送通知"""
        pass

class InAppChannel(NotificationChannel):
    """站内信渠道"""
    
    def send(self, user_id: int, subject: str, body: str) -> bool:
        # 存储到数据库
        return True

class EmailChannel(NotificationChannel):
    """邮件渠道"""
    
    def send(self, user_id: int, subject: str, body: str) -> bool:
        # 发送邮件（占位实现）
        print(f"[Email] To: {user_id}, Subject: {subject}")
        return True

class SmsChannel(NotificationChannel):
    """短信渠道（预留）"""
    
    def send(self, user_id: int, subject: str, body: str) -> bool:
        # 预留实现
        return True

# 渠道注册表
CHANNEL_REGISTRY = {
    "in_app": InAppChannel(),
    "email": EmailChannel(),
    "sms": SmsChannel(),
}
```

### 4. 通知处理器

**文件**：`app/modules/notifications/handlers.py`

```python
from app.core.eventbus import Event
from app.modules.notifications.channels import CHANNEL_REGISTRY
from app.modules.notifications.repository import get_template

class NotificationHandler:
    """事件驱动的通知处理器"""
    
    def handle_event(self, event: Event):
        """处理事件，发送通知"""
        template_name = event.event_type
        
        # 查询所有活跃渠道
        for channel_name, channel in CHANNEL_REGISTRY.items():
            # 查询模板
            template = get_template(template_name, channel_name)
            if not template or not template.is_active:
                continue
            
            # 渲染模板
            subject = self._render(template.subject, event.data)
            body = self._render(template.body, event.data)
            
            # 发送通知
            user_id = event.data.get("user_id")
            if user_id:
                channel.send(user_id, subject, body)
    
    def _render(self, template: str, context: dict) -> str:
        """简单模板渲染"""
        for key, value in context.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template

# 全局处理器
notification_handler = NotificationHandler()
```

## Data Model

### 1. NotificationTemplate（通知模板）

```python
# app/modules/notifications/models.py
from sqlalchemy import Column, Integer, String, Text, Boolean
from app.db.base import UserBase

class NotificationTemplate(UserBase):
    __tablename__ = "notification_templates"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # 模板名：order.confirmed
    channel = Column(String(20), nullable=False)             # 渠道：in_app, email, sms
    subject = Column(String(200))                            # 邮件主题
    body = Column(Text, nullable=False)                      # 模板内容（支持变量）
    is_active = Column(Boolean, default=True)
```

### 2. Notification（通知记录）

```python
class Notification(UserBase):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    template_name = Column(String(100), nullable=False)
    channel = Column(String(20), nullable=False)
    status = Column(String(20), default="pending")  # pending, sent, failed
    subject = Column(String(200))
    body = Column(Text)
    is_read = Column(Boolean, default=False)
    error_message = Column(Text)
    sent_at = Column(DateTime)
```

### 3. NotificationPreference（用户偏好 - 预留）

```python
class NotificationPreference(UserBase):
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    in_app_enabled = Column(Boolean, default=True)
```

## API Routes

### 用户通知接口（需要认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/notifications/` | 获取我的通知列表 |
| GET | `/api/v1/notifications/{id}` | 获取通知详情 |
| PUT | `/api/v1/notifications/{id}/read` | 标记已读 |
| PUT | `/api/v1/notifications/read-all` | 全部标记已读 |

### 模板管理接口（仅管理员）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/notifications/templates` | 获取模板列表 |
| POST | `/api/v1/notifications/templates` | 创建模板 |
| PUT | `/api/v1/notifications/templates/{id}` | 更新模板 |
| DELETE | `/api/v1/notifications/templates/{id}` | 删除模板 |

### 响应格式

```json
{
  "success": true,
  "data": {
    "id": 1,
    "user_id": 1,
    "template_name": "order.confirmed",
    "channel": "in_app",
    "subject": "订单已确认",
    "body": "您的订单 #123 已确认",
    "status": "sent",
    "is_read": false,
    "created_at": "2026-03-27T10:00:00Z"
  }
}
```

## Event Integration

### 订单模块集成

**文件**：`app/modules/orders/service.py`

```python
from app.core.eventbus import eventbus, Event
from app.core.events import ORDER_CONFIRMED, ORDER_SHIPPED, ORDER_CANCELLED

async def update_order_status(session, order_id, data):
    # ... 现有逻辑 ...
    
    # 发布事件
    if data.status == OrderStatus.CONFIRMED:
        eventbus.publish(Event(
            event_type=ORDER_CONFIRMED,
            data={"order_id": order_id, "user_id": order.user_id}
        ))
    
    return order
```

## File Structure

```
app/
├── core/
│   ├── eventbus.py          # 事件总线
│   └── events.py            # 事件类型定义
└── modules/
    └── notifications/
        ├── __init__.py
        ├── models.py        # 数据模型
        ├── schemas.py       # Pydantic schemas
        ├── repository.py    # 数据访问层
        ├── service.py       # 业务逻辑层
        ├── router.py        # API 路由
        ├── channels.py      # 通知渠道
        └── handlers.py      # 事件处理器
```

## Implementation Order

1. **Phase 1**: 核心基础设施
   - EventBus (`app/core/eventbus.py`)
   - 事件类型 (`app/core/events.py`)
   - 数据模型 (`models.py`)

2. **Phase 2**: 通知渠道
   - 渠口接口 (`channels.py`)
   - 事件处理器 (`handlers.py`)

3. **Phase 3**: 数据层
   - Repository (`repository.py`)
   - Schemas (`schemas.py`)

4. **Phase 4**: 业务层
   - Service (`service.py`)
   - Router (`router.py`)

5. **Phase 5**: 集成
   - 订单模块集成
   - 用户模块集成
   - 任务模块集成

6. **Phase 6**: 测试
   - 单元测试
   - 集成测试

## Success Criteria

1. EventBus 可发布和订阅事件
2. 订单状态变更触发通知
3. 通知记录存储到数据库
4. 用户可查询通知列表
5. 用户可标记通知已读
6. 管理员可管理通知模板
7. 所有测试通过
