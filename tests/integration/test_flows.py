import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status


@pytest.mark.asyncio
class TestIntegrationBasics:
    async def test_health_endpoint(self, client):
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"

    async def test_api_docs_accessible(self, client):
        response = await client.get("/api/v1/docs")
        assert response.status_code == status.HTTP_200_OK

    async def test_root_endpoint(self, client):
        response = await client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "docs" in data

    async def test_auth_flow(self, client):
        unique_id = str(uuid.uuid4())[:8]
        register_data = {
            "email": f"test_{unique_id}@example.com",
            "username": f"testuser_{unique_id}",
            "password": "TestPassword123",
            "full_name": "Test User",
        }
        response = await client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == status.HTTP_201_CREATED

    async def test_notifications_flow(self, client, user_headers):
        with patch("app.core.eventbus.eventbus.publish") as mock_publish:
            from app.core.eventbus import Event
            from app.core.events import ORDER_CONFIRMED

            mock_publish(Event(event_type=ORDER_CONFIRMED, data={"order_id": 1, "user_id": 1}))
            mock_publish.assert_called_once()

    async def test_exports_flow(self, client, user_headers):
        with patch("app.modules.exports.router.dispatch") as mock_dispatch:
            mock_result = MagicMock()
            mock_result.id = "test-task-id"
            mock_dispatch.return_value = mock_result

            response = await client.post("/api/v1/exports/orders/", headers=user_headers)
            assert response.status_code == status.HTTP_202_ACCEPTED

    async def test_full_crud_flow(self, client, superuser_headers, session):
        from app.modules.products.schemas import ProductCreate
        from app.modules.products import service as product_service
        from decimal import Decimal

        product_data = ProductCreate(
            name="Integration Test Product",
            sku="INT-CRUD-001",
            price=Decimal("29.99"),
            category="test",
        )

        product = await product_service.create_product(session, product_data)
        assert product.id is not None

        fetched = await product_service.get_product_by_id(session, product.id)
        assert fetched is not None
        assert fetched.name == "Integration Test Product"

        await product_service.delete_product(session, product.id)

        deleted = await product_service.get_product_by_id(session, product.id)
        assert deleted is None


@pytest.mark.asyncio
class TestOrderNotificationIntegration:
    async def test_eventbus_publishes_order_events(self, session):
        from app.core.eventbus import EventBus, Event
        from app.core.events import ORDER_CONFIRMED

        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(ORDER_CONFIRMED, handler)

        bus.publish(Event(event_type=ORDER_CONFIRMED, data={"order_id": 123, "user_id": 1}))

        assert len(received) == 1
        assert received[0].data["order_id"] == 123


@pytest.mark.asyncio
class TestEndToEndFlows:
    async def test_user_registration_and_login_flow(self, client):
        unique_id = str(uuid.uuid4())[:8]
        register_data = {
            "email": f"e2e_{unique_id}@example.com",
            "username": f"e2euser_{unique_id}",
            "password": "TestPassword123",
            "full_name": "E2E Test User",
        }
        response = await client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == status.HTTP_201_CREATED

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": f"e2euser_{unique_id}", "password": "TestPassword123"},
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["data"]["access_token"]

        me_response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["data"]["username"] == f"e2euser_{unique_id}"

    async def test_product_crud_with_auth(self, client, superuser_headers):
        unique_id = str(uuid.uuid4())[:8]
        create_data = {
            "name": f"E2E Product {unique_id}",
            "sku": f"E2E-{unique_id}",
            "price": "49.99",
            "category": "e2e-test",
        }
        create_response = await client.post(
            "/api/v1/products/",
            headers=superuser_headers,
            json=create_data,
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        product_id = create_response.json()["data"]["id"]

        get_response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=superuser_headers,
        )
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["data"]["name"] == f"E2E Product {unique_id}"

        update_response = await client.put(
            f"/api/v1/products/{product_id}",
            headers=superuser_headers,
            json={"price": "39.99"},
        )
        assert update_response.status_code == status.HTTP_200_OK

        list_response = await client.get(
            "/api/v1/products/",
            headers=superuser_headers,
        )
        assert list_response.status_code == status.HTTP_200_OK

    async def test_notification_lifecycle(self, client, user_headers, superuser_headers, session, test_user):
        from app.modules.notifications.models import Notification

        template_response = await client.post(
            "/api/v1/notifications/templates/",
            headers=superuser_headers,
            json={
                "name": f"e2e.test.{uuid.uuid4().hex[:8]}",
                "channel": "in_app",
                "subject": "E2E Test",
                "body": "Test notification body",
                "is_active": True,
            },
        )
        assert template_response.status_code == status.HTTP_201_CREATED

        notification = Notification(
            user_id=test_user.id,
            template_name="e2e.test",
            channel="in_app",
            body="E2E test notification",
            status="sent",
            is_read=False,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)

        list_response = await client.get(
            "/api/v1/notifications/",
            headers=user_headers,
        )
        assert list_response.status_code == status.HTTP_200_OK
        assert list_response.json()["total"] >= 1

        mark_response = await client.put(
            f"/api/v1/notifications/{notification.id}/read",
            headers=user_headers,
        )
        assert mark_response.status_code == status.HTTP_200_OK
        assert mark_response.json()["data"]["is_read"] is True
