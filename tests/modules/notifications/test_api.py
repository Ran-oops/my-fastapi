import uuid

import pytest
from fastapi import status

from app.modules.notifications.models import Notification, NotificationTemplate


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

    async def test_create_template_admin(self, client, superuser_headers):
        unique_id = str(uuid.uuid4())[:8]
        response = await client.post(
            "/api/v1/notifications/templates/",
            headers=superuser_headers,
            json={
                "name": f"test.created.{unique_id}",
                "channel": "in_app",
                "subject": "Test Subject",
                "body": "Test Body",
                "is_active": True,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["name"] == f"test.created.{unique_id}"

    async def test_create_template_duplicate_name(self, client, superuser_headers, session):
        unique_name = f"duplicate.test.{uuid.uuid4().hex[:8]}"
        template = NotificationTemplate(
            name=unique_name,
            channel="in_app",
            body="Existing",
            is_active=True,
        )
        session.add(template)
        await session.commit()

        response = await client.post(
            "/api/v1/notifications/templates/",
            headers=superuser_headers,
            json={
                "name": unique_name,
                "channel": "email",
                "body": "New",
                "is_active": True,
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_update_template_admin(self, client, superuser_headers, session):
        template = NotificationTemplate(
            name=f"update.test.{uuid.uuid4().hex[:8]}",
            channel="in_app",
            body="Original",
            is_active=True,
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)

        response = await client.put(
            f"/api/v1/notifications/templates/{template.id}",
            headers=superuser_headers,
            json={"body": "Updated Body"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["body"] == "Updated Body"

    async def test_delete_template_admin(self, client, superuser_headers, session):
        template = NotificationTemplate(
            name=f"delete.test.{uuid.uuid4().hex[:8]}",
            channel="in_app",
            body="To delete",
            is_active=True,
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)

        response = await client.delete(
            f"/api/v1/notifications/templates/{template.id}",
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_mark_notification_read(self, client, user_headers, session, test_user):
        notification = Notification(
            user_id=test_user.id,
            template_name="test.read",
            channel="in_app",
            body="Test notification",
            status="sent",
            is_read=False,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)

        response = await client.put(
            f"/api/v1/notifications/{notification.id}/read",
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["is_read"] is True

    async def test_mark_all_read(self, client, user_headers, session, test_user):
        for i in range(3):
            notification = Notification(
                user_id=test_user.id,
                template_name=f"test.all.{i}.{uuid.uuid4().hex[:8]}",
                channel="in_app",
                body=f"Notification {i}",
                status="sent",
                is_read=False,
            )
            session.add(notification)
        await session.commit()

        response = await client.put(
            "/api/v1/notifications/read-all",
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["marked_count"] == 3

    async def test_get_notification_by_id(self, client, user_headers, session, test_user):
        notification = Notification(
            user_id=test_user.id,
            template_name="test.get",
            channel="in_app",
            body="Test notification",
            status="sent",
            is_read=False,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)

        response = await client.get(
            f"/api/v1/notifications/{notification.id}",
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == notification.id

    async def test_get_notification_unread_only(self, client, user_headers, session, test_user):
        for i in range(2):
            notification = Notification(
                user_id=test_user.id,
                template_name=f"test.unread.{i}.{uuid.uuid4().hex[:8]}",
                channel="in_app",
                body=f"Notification {i}",
                status="sent",
                is_read=i == 1,
            )
            session.add(notification)
        await session.commit()

        response = await client.get(
            "/api/v1/notifications/?is_read=false",
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
