import pytest
from unittest.mock import patch, MagicMock
from fastapi import status


@pytest.mark.asyncio
class TestExportsAPI:
    async def test_export_orders_unauthorized(self, client):
        response = await client.post("/api/v1/exports/orders/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_export_orders_success(self, client, user_headers):
        with patch("app.modules.exports.router.dispatch") as mock_dispatch:
            mock_result = MagicMock()
            mock_result.id = "test-task-id"
            mock_dispatch.return_value = mock_result

            response = await client.post("/api/v1/exports/orders/?format=csv", headers=user_headers)
            assert response.status_code == status.HTTP_202_ACCEPTED
            data = response.json()
            assert "data" in data
            assert "task_id" in data["data"]
            assert "status" in data["data"]

    async def test_export_products_success(self, client, user_headers):
        with patch("app.modules.exports.router.dispatch") as mock_dispatch:
            mock_result = MagicMock()
            mock_result.id = "test-task-id"
            mock_dispatch.return_value = mock_result

            response = await client.post("/api/v1/exports/products/?format=json", headers=user_headers)
            assert response.status_code == status.HTTP_202_ACCEPTED

    async def test_export_audit_forbidden(self, client, user_headers):
        response = await client.post("/api/v1/exports/audit/", headers=user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_export_audit_admin(self, client, superuser_headers):
        with patch("app.modules.exports.router.dispatch") as mock_dispatch:
            mock_result = MagicMock()
            mock_result.id = "test-task-id"
            mock_dispatch.return_value = mock_result

            response = await client.post("/api/v1/exports/audit/?format=csv", headers=superuser_headers)
            assert response.status_code == status.HTTP_202_ACCEPTED

    async def test_export_orders_with_filters(self, client, user_headers):
        with patch("app.modules.exports.router.dispatch") as mock_dispatch:
            mock_result = MagicMock()
            mock_result.id = "test-task-id"
            mock_dispatch.return_value = mock_result

            response = await client.post(
                "/api/v1/exports/orders/?format=csv&status=PENDING&limit=100", headers=user_headers
            )
            assert response.status_code == status.HTTP_202_ACCEPTED

            call_args = mock_dispatch.call_args
            assert call_args[0][1].get("status") == "PENDING"
            assert call_args[0][1].get("limit") == 100
