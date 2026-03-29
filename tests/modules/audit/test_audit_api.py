import pytest
from fastapi import status

from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestAuditAPIList:
    async def test_get_audit_logs_admin_success(self, client, superuser_headers):
        response = await client.get("/api/v1/audit/", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data

    async def test_get_audit_logs_filter_by_user(self, client, test_user, superuser_headers, multiple_audit_logs):
        response = await client.get(f"/api/v1/audit/?user_id={test_user.id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        for log in response.json()["data"]:
            assert log["user_id"] == test_user.id

    async def test_get_audit_logs_filter_by_resource(self, client, superuser_headers):
        response = await client.get("/api/v1/audit/?resource_type=product&resource_id=1", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "data" in response.json()

    async def test_get_audit_logs_unauthorized(self, client):
        assert (await client.get("/api/v1/audit/")).status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_audit_logs_forbidden(self, client, user_headers):
        assert (await client.get("/api/v1/audit/", headers=user_headers)).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestAuditAPIGetById:
    async def test_get_audit_log_by_id_admin_success(self, client, superuser_headers, test_audit_log):
        response = await client.get(f"/api/v1/audit/{test_audit_log.id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["id"] == test_audit_log.id

    async def test_get_audit_log_by_id_not_found(self, client, superuser_headers):
        assert (
            await client.get(f"/api/v1/audit/{NONEXISTENT_ID}", headers=superuser_headers)
        ).status_code == status.HTTP_404_NOT_FOUND

    async def test_get_audit_log_by_id_unauthorized(self, client):
        assert (await client.get("/api/v1/audit/1")).status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_audit_log_by_id_forbidden(self, client, user_headers):
        assert (await client.get("/api/v1/audit/1", headers=user_headers)).status_code == status.HTTP_403_FORBIDDEN
