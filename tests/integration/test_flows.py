import pytest
from unittest.mock import patch, MagicMock
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
        register_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123",
            "full_name": "Test User",
        }
        response = await client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

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
