import pytest
from fastapi import status


@pytest.mark.asyncio
class TestExportsAPI:
    async def test_export_orders_unauthorized(self, client):
        response = await client.post("/api/v1/exports/orders/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_export_orders_success(self, client, user_headers, mock_export_dispatch):
        response = await client.post("/api/v1/exports/orders/?format=csv", headers=user_headers)
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "data" in data
        assert "task_id" in data["data"]
        assert "status" in data["data"]

    async def test_export_products_success(self, client, user_headers, mock_export_dispatch):
        response = await client.post("/api/v1/exports/products/?format=json", headers=user_headers)
        assert response.status_code == status.HTTP_202_ACCEPTED

    async def test_export_audit_forbidden(self, client, user_headers):
        response = await client.post("/api/v1/exports/audit/", headers=user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_export_audit_admin(self, client, superuser_headers, mock_export_dispatch):
        response = await client.post("/api/v1/exports/audit/?format=csv", headers=superuser_headers)
        assert response.status_code == status.HTTP_202_ACCEPTED

    async def test_export_orders_with_filters(self, client, user_headers, mock_export_dispatch):
        response = await client.post(
            "/api/v1/exports/orders/?format=csv&order_status=PENDING&limit=100", headers=user_headers
        )
        assert response.status_code == status.HTTP_202_ACCEPTED

        call_args = mock_export_dispatch.call_args
        assert call_args[0][1].get("status") == "PENDING"
        assert call_args[0][1].get("limit") == 100

    async def test_export_invalid_format(self, client, user_headers):
        response = await client.post("/api/v1/exports/orders/?format=invalid", headers=user_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_export_excel_format(self, client, user_headers, mock_export_dispatch):
        response = await client.post("/api/v1/exports/products/?format=excel", headers=user_headers)
        assert response.status_code == status.HTTP_202_ACCEPTED

    async def test_get_task_status(self, client, user_headers, mock_celery_success):
        response = await client.get("/api/v1/exports/status/test-task-id", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["status"] == "SUCCESS"
        assert data["data"]["result"]["count"] == 10

    async def test_get_task_status_pending(self, client, user_headers, mock_celery_pending):
        response = await client.get("/api/v1/exports/status/pending-task", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["status"] == "PENDING"

    async def test_get_task_status_unauthorized(self, client):
        response = await client.get("/api/v1/exports/status/test-task-id")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
