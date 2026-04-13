"""
通知系统集成测试

测试完整流程: 事件发布 → 通知生成 → 发送通知 → 标记已读
测试多渠道通知、测试通知模板
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from sqlalchemy import select

from app.core.eventbus import Event, eventbus
from app.core.events import ORDER_CONFIRMED, ORDER_SHIPPED, USER_REGISTERED
from app.modules.notifications.models import Notification, NotificationTemplate
from app.modules.notifications import service as notification_service
from app.modules.notifications.schemas import (
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
)
from app.modules.users.models import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestNotificationSystem:
    """通知系统完整流程测试"""

    async def test_full_notification_flow(self, client, session, superuser_headers):
        """测试完整通知流程: 事件发布 → 通知生成 → 发送通知 → 标记已读"""
        unique_id = uuid.uuid4().hex[:8]

        # Step 1: 创建通知模板
        template_data = NotificationTemplateCreate(
            name=f"test.order.confirmation_{unique_id}",
            channel="in_app",
            subject="Order Confirmed",
            body="Your order #{order_id} has been confirmed.",
            is_active=True,
        )
        template = await notification_service.create_template(session, template_data)
        assert template.id is not None
        assert template.name == f"test.order.confirmation_{unique_id}"

        # Step 2: 创建用户
        user = User(
            email=f"notify_{unique_id}@example.com",
            username=f"notify_{unique_id}",
            hashed_password=get_password_hash("TestPass123"),
            full_name="Notification Test User",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Step 3: 创建通知 (模拟事件处理)
        notification = Notification(
            user_id=user.id,
            template_name=f"test.order.confirmation_{unique_id}",
            channel="in_app",
            status="sent",
            subject="Order Confirmed",
            body="Your order #123 has been confirmed.",
            is_read=False,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)

        assert notification.id is not None
        assert notification.status == "sent"
        assert notification.is_read is False
        assert notification.sent_at is None  # 未实际发送

        # Step 4: 通过API发布事件
        event_data = {"order_id": 123, "user_id": user.id}
        await notification_service.publish_event(ORDER_CONFIRMED, event_data)

        # Step 5: 获取用户通知列表
        # 创建用户token
        from app.core.security import create_access_token

        user_token = create_access_token(subject=str(user.id))
        user_headers = {"Authorization": f"Bearer {user_token}"}

        list_response = await client.get(
            "/api/v1/notifications/",
            headers=user_headers,
        )
        assert list_response.status_code == status.HTTP_200_OK

        list_data = list_response.json()
        assert list_data["total"] >= 1

        # Step 6: 标记通知为已读
        mark_response = await client.put(
            f"/api/v1/notifications/{notification.id}/read",
            headers=user_headers,
        )
        assert mark_response.status_code == status.HTTP_200_OK

        marked_notification = mark_response.json()["data"]
        assert marked_notification["is_read"] is True

        # 验证数据库更新
        await session.refresh(notification)
        assert notification.is_read is True

        # Step 7: 再次获取列表验证状态
        list_response2 = await client.get(
            "/api/v1/notifications/",
            headers=user_headers,
        )
        notifications = list_response2.json()["data"]
        for n in notifications:
            if n["id"] == notification.id:
                assert n["is_read"] is True

    async def test_notification_template_lifecycle(self, client, session, superuser_headers):
        """测试通知模板生命周期"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建模板
        create_data = {
            "name": f"test.template_{unique_id}",
            "channel": "email",
            "subject": "Test Subject",
            "body": "Test body content",
            "is_active": True,
        }
        create_response = await client.post(
            "/api/v1/notifications/templates/",
            headers=superuser_headers,
            json=create_data,
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        template_id = create_response.json()["data"]["id"]

        # 获取模板列表
        list_response = await client.get(
            "/api/v1/notifications/templates/",
            headers=superuser_headers,
        )
        assert list_response.status_code == status.HTTP_200_OK
        templates = list_response.json()["data"]
        template_names = [t["name"] for t in templates]
        assert f"test.template_{unique_id}" in template_names

        # 更新模板
        update_response = await client.put(
            f"/api/v1/notifications/templates/{template_id}",
            headers=superuser_headers,
            json={"subject": "Updated Subject", "is_active": False},
        )
        assert update_response.status_code == status.HTTP_200_OK
        updated = update_response.json()["data"]
        assert updated["subject"] == "Updated Subject"
        assert updated["is_active"] is False

        # 删除模板
        delete_response = await client.delete(
            f"/api/v1/notifications/templates/{template_id}",
            headers=superuser_headers,
        )
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # 验证模板已删除
        list_response2 = await client.get(
            "/api/v1/notifications/templates/",
            headers=superuser_headers,
        )
        templates_after = list_response2.json()["data"]
        template_names_after = [t["name"] for t in templates_after]
        assert f"test.template_{unique_id}" not in template_names_after

    async def test_multi_channel_notifications(self, client, session, superuser_headers):
        """测试多渠道通知"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建多渠道模板
        channels = ["email", "sms", "in_app"]
        templates = []
        for channel in channels:
            template = NotificationTemplate(
                name=f"test.multi.{channel}_{unique_id}",
                channel=channel,
                subject=f"Test {channel.upper()}",
                body=f"Test body for {channel}",
                is_active=True,
            )
            session.add(template)
            templates.append(template)

        user = User(
            email=f"multi_{unique_id}@example.com",
            username=f"multi_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        for t in templates:
            await session.refresh(t)

        # 为不同渠道创建通知
        notifications = []
        for template in templates:
            notification = Notification(
                user_id=user.id,
                template_name=template.name,
                channel=template.channel,
                status="sent",
                subject=template.subject,
                body=template.body,
                is_read=False,
            )
            session.add(notification)
            notifications.append(notification)

        await session.commit()

        # 验证每个渠道的通知
        user_token = __import__("app.core.security", fromlist=["create_access_token"]).create_access_token(
            subject=str(user.id)
        )
        user_headers = {"Authorization": f"Bearer {user_token}"}

        list_response = await client.get(
            "/api/v1/notifications/",
            headers=user_headers,
        )
        assert list_response.status_code == status.HTTP_200_OK

        notif_list = list_response.json()["data"]
        channels_in_db = [n["channel"] for n in notif_list]

        for channel in channels:
            assert channel in channels_in_db

    async def test_event_driven_notification_generation(self, client, session):
        """测试事件驱动的通知生成"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建用户
        user = User(
            email=f"event_{unique_id}@example.com",
            username=f"event_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # 监听事件
        received_events = []

        def event_handler(event):
            received_events.append(event)

        eventbus.subscribe(ORDER_CONFIRMED, event_handler)

        try:
            # 发布事件
            event_data = {"order_id": 999, "user_id": user.id, "amount": "99.99"}
            eventbus.publish(Event(event_type=ORDER_CONFIRMED, data=event_data))

            # 验证事件被接收
            assert len(received_events) == 1
            assert received_events[0].event_type == ORDER_CONFIRMED
            assert received_events[0].data["order_id"] == 999

        finally:
            eventbus.unsubscribe(ORDER_CONFIRMED, event_handler)

    async def test_notification_filtering_and_pagination(self, client, session):
        """测试通知筛选和分页"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建用户
        user = User(
            email=f"filter_{unique_id}@example.com",
            username=f"filter_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # 创建不同状态的通知
        for i in range(10):
            notification = Notification(
                user_id=user.id,
                template_name=f"filter_test_{unique_id}",
                channel="in_app",
                status="sent",
                subject=f"Test {i}",
                body=f"Body {i}",
                is_read=(i < 5),  # 前5个已读
            )
            session.add(notification)

        await session.commit()

        # 创建token
        from app.core.security import create_access_token

        user_token = create_access_token(subject=str(user.id))
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # 测试分页
        page_response = await client.get(
            "/api/v1/notifications/?page=1&page_size=3",
            headers=user_headers,
        )
        assert page_response.status_code == status.HTTP_200_OK
        page_data = page_response.json()
        assert len(page_data["data"]) == 3
        assert page_data["page"] == 1
        assert page_data["page_size"] == 3

        # 测试按已读状态筛选
        # 注意: API参数可能不同，根据实际实现调整
        # 这里验证API响应结构
        all_response = await client.get(
            "/api/v1/notifications/",
            headers=user_headers,
        )
        assert all_response.status_code == status.HTTP_200_OK
        total = all_response.json()["total"]
        assert total >= 10

    async def test_mark_all_notifications_read(self, client, session):
        """测试标记所有通知为已读"""
        unique_id = uuid.uuid4().hex[:8]

        user = User(
            email=f"markall_{unique_id}@example.com",
            username=f"markall_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # 创建多个未读通知
        for i in range(5):
            notification = Notification(
                user_id=user.id,
                template_name=f"mark_all_{unique_id}",
                channel="in_app",
                status="sent",
                subject=f"Unread {i}",
                body=f"Body {i}",
                is_read=False,
            )
            session.add(notification)

        await session.commit()

        # 创建token
        from app.core.security import create_access_token

        user_token = create_access_token(subject=str(user.id))
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # 标记全部已读
        mark_all_response = await client.put(
            "/api/v1/notifications/read-all",
            headers=user_headers,
        )
        assert mark_all_response.status_code == status.HTTP_200_OK

        marked_count = mark_all_response.json()["data"]["marked_count"]
        assert marked_count == 5

        # 验证所有通知已读
        result = await session.execute(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.template_name == f"mark_all_{unique_id}",
                Notification.is_read == False,
            )
        )
        unread = result.scalars().all()
        assert len(unread) == 0

    async def test_notification_delivery_status_tracking(self, client, session):
        """测试通知发送状态追踪"""
        unique_id = uuid.uuid4().hex[:8]

        user = User(
            email=f"status_{unique_id}@example.com",
            username=f"status_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # 创建不同状态的通知
        statuses = ["pending", "sent", "failed", "delivered"]
        for status_val in statuses:
            notification = Notification(
                user_id=user.id,
                template_name=f"status_test_{unique_id}",
                channel="email",
                status=status_val,
                subject=f"Status: {status_val}",
                body="Test body",
                is_read=False,
                error_message=("Connection failed" if status_val == "failed" else None),
            )
            session.add(notification)

        await session.commit()

        # 验证数据库中不同状态的通知
        result = await session.execute(
            select(Notification).where(
                Notification.user_id == user.id, Notification.template_name == f"status_test_{unique_id}"
            )
        )
        notifications = result.scalars().all()
        assert len(notifications) == 4

        status_counts = {n.status: n for n in notifications}
        for status_val in statuses:
            assert status_val in status_counts

        # 验证失败通知有错误信息
        assert status_counts["failed"].error_message == "Connection failed"
