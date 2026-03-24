import pytest
from fastapi import status


@pytest.mark.asyncio
class TestPermissionCRUD:
    async def test_create_permission_success(self, client, superuser_token):
        response = await client.post(
            "/api/v1/permissions/",
            json={"name": "Read Users", "code": "users:read", "description": "Can read user data"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Read Users"
        assert data["data"]["code"] == "users:read"

    async def test_create_permission_duplicate_code(self, client, superuser_token):
        await client.post(
            "/api/v1/permissions/",
            json={"name": "Write Users", "code": "users:write"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        response = await client.post(
            "/api/v1/permissions/",
            json={"name": "Another Write", "code": "users:write"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already exists" in data["detail"]

    async def test_get_permissions(self, client, superuser_token):
        await client.post(
            "/api/v1/permissions/",
            json={"name": "Delete Users", "code": "users:delete"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        response = await client.get(
            "/api/v1/permissions/",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0

    async def test_get_permission_by_id(self, client, superuser_token):
        create_response = await client.post(
            "/api/v1/permissions/",
            json={"name": "Update Users", "code": "users:update"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        permission_id = create_response.json()["data"]["id"]
        response = await client.get(
            f"/api/v1/permissions/{permission_id}",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == permission_id
        assert data["data"]["code"] == "users:update"

    async def test_update_permission(self, client, superuser_token):
        create_response = await client.post(
            "/api/v1/permissions/",
            json={"name": "List Users", "code": "users:list", "description": "Old description"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        permission_id = create_response.json()["data"]["id"]
        response = await client.put(
            f"/api/v1/permissions/{permission_id}",
            json={"description": "Updated description"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["description"] == "Updated description"

    async def test_delete_permission(self, client, superuser_token):
        create_response = await client.post(
            "/api/v1/permissions/",
            json={"name": "Temporary", "code": "temp:permission"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        permission_id = create_response.json()["data"]["id"]
        response = await client.delete(
            f"/api/v1/permissions/{permission_id}",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_create_permission_forbidden(self, client, user_token):
        response = await client.post(
            "/api/v1/permissions/",
            json={"name": "Unauthorized", "code": "unauthorized:code"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestRolePermissions:
    async def test_get_role_permissions(self, client, superuser_token):
        await client.post(
            "/api/v1/permissions/",
            json={"name": "View Reports", "code": "reports:view"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        role_response = await client.post(
            "/api/v1/roles/",
            json={"name": "report_viewer", "description": "Can view reports"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        role_id = role_response.json()["data"]["id"]
        response = await client.get(
            f"/api/v1/permissions/roles/{role_id}",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
