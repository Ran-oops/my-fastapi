import pytest
from fastapi import status


@pytest.mark.asyncio
class TestRoleCRUD:
    async def test_create_role_success(self, client, superuser_token):
        response = await client.post(
            "/api/v1/roles/",
            json={"name": "admin", "description": "Administrator role"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "admin"
        assert data["data"]["description"] == "Administrator role"

    async def test_create_role_duplicate_name(self, client, superuser_token):
        await client.post(
            "/api/v1/roles/",
            json={"name": "duplicate_role", "description": "First role"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        response = await client.post(
            "/api/v1/roles/",
            json={"name": "duplicate_role", "description": "Second role"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already exists" in data["detail"]

    async def test_get_roles(self, client, superuser_token):
        await client.post(
            "/api/v1/roles/",
            json={"name": "viewer", "description": "Viewer role"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        response = await client.get(
            "/api/v1/roles/",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0

    async def test_get_role_by_id(self, client, superuser_token):
        create_response = await client.post(
            "/api/v1/roles/",
            json={"name": "editor", "description": "Editor role"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        role_id = create_response.json()["data"]["id"]
        response = await client.get(
            f"/api/v1/roles/{role_id}",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == role_id
        assert data["data"]["name"] == "editor"

    async def test_update_role(self, client, superuser_token):
        create_response = await client.post(
            "/api/v1/roles/",
            json={"name": "manager", "description": "Manager role"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        role_id = create_response.json()["data"]["id"]
        response = await client.put(
            f"/api/v1/roles/{role_id}",
            json={"description": "Updated manager role"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["description"] == "Updated manager role"

    async def test_delete_role(self, client, superuser_token):
        create_response = await client.post(
            "/api/v1/roles/",
            json={"name": "temporary", "description": "Temporary role"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        role_id = create_response.json()["data"]["id"]
        response = await client.delete(
            f"/api/v1/roles/{role_id}",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_create_role_forbidden(self, client, user_token):
        response = await client.post(
            "/api/v1/roles/",
            json={"name": "unauthorized", "description": "Should not create"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestRoleAssignment:
    async def test_assign_role_to_user(self, client, superuser_token, user_id):
        role_response = await client.post(
            "/api/v1/roles/",
            json={"name": "test_role", "description": "Test role"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        role_id = role_response.json()["data"]["id"]
        response = await client.post(
            "/api/v1/roles/assign",
            json={"user_id": user_id, "role_id": role_id},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    async def test_remove_role_from_user(self, client, superuser_token, user_id):
        role_response = await client.post(
            "/api/v1/roles/",
            json={"name": "remove_role", "description": "Role to remove"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        role_id = role_response.json()["data"]["id"]
        await client.post(
            "/api/v1/roles/assign",
            json={"user_id": user_id, "role_id": role_id},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        response = await client.delete(
            f"/api/v1/roles/assign/{user_id}/{role_id}",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_get_user_roles(self, client, superuser_token, user_id):
        response = await client.get(
            f"/api/v1/roles/users/{user_id}",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
