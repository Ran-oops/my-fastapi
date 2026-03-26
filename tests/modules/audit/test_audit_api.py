import pytest
from fastapi import status


@pytest.mark.asyncio
class TestAuditAPIList:
    async def test_get_audit_logs_admin_success(self, client, superuser_headers):
        response = await client.get("/api/v1/audit/", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    async def test_get_audit_logs_filter_by_user(self, client, superuser_headers, multiple_audit_logs):
        response = await client.get("/api/v1/audit/?user_id=1", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        for log in data["data"]:
            assert log["user_id"] == 1

    async def test_get_audit_logs_filter_by_resource(self, client, superuser_headers):
        response = await client.get("/api/v1/audit/?resource_type=product&resource_id=1", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data

    async def test_get_audit_logs_unauthorized(self, client):
        response = await client.get("/api/v1/audit/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_audit_logs_forbidden(self, client, user_headers):
        response = await client.get("/api/v1/audit/", headers=user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestAuditAPIGetById:
    async def test_get_audit_log_by_id_admin_success(self, client, superuser_headers, test_audit_log):
        response = await client.get(f"/api/v1/audit/{test_audit_log.id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == test_audit_log.id
        assert data["data"]["action"] == test_audit_log.action

    async def test_get_audit_log_by_id_not_found(self, client, superuser_headers):
        response = await client.get("/api/v1/audit/99999", headers=superuser_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_audit_log_by_id_unauthorized(self, client):
        response = await client.get("/api/v1/audit/1")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_audit_log_by_id_forbidden(self, client, user_headers):
        response = await client.get("/api/v1/audit/1", headers=user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
