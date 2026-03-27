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
