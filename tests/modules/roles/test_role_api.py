import uuid

import pytest
from fastapi import status

from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestRoleAPIList:
    async def test_get_roles_success(self, client, superuser_headers):
        response = await client.get("/api/v1/roles/", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data

    async def test_get_roles_unauthorized(self, client):
        response = await client.get("/api/v1/roles/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_roles_user_allowed(self, client, user_headers):
        response = await client.get("/api/v1/roles/", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
class TestRoleAPIGetById:
    async def test_get_role_by_id_success(self, client, superuser_headers):
        unique_id = uuid.uuid4().hex[:8]
        create_response = await client.post(
            "/api/v1/roles/",
            json={"name": f"get_role_{unique_id}", "description": "Get role test"},
            headers=superuser_headers,
        )
        role_id = create_response.json()["data"]["id"]

        response = await client.get(f"/api/v1/roles/{role_id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["id"] == role_id

    async def test_get_role_by_id_not_found(self, client, superuser_headers):
        response = await client.get(f"/api/v1/roles/{NONEXISTENT_ID}", headers=superuser_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_role_by_id_unauthorized(self, client):
        response = await client.get("/api/v1/roles/1")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestRoleAPICreate:
    async def test_create_role_success(self, client, superuser_headers):
        unique_id = uuid.uuid4().hex[:8]
        response = await client.post(
            "/api/v1/roles/",
            json={"name": f"api_role_{unique_id}", "description": "API test role"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["name"] == f"api_role_{unique_id}"

    async def test_create_role_duplicate_name(self, client, superuser_headers):
        unique_id = uuid.uuid4().hex[:8]
        await client.post(
            "/api/v1/roles/",
            json={"name": f"duplicate_{unique_id}", "description": "First"},
            headers=superuser_headers,
        )
        response = await client.post(
            "/api/v1/roles/",
            json={"name": f"duplicate_{unique_id}", "description": "Second"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_create_role_unauthorized(self, client):
        response = await client.post("/api/v1/roles/", json={"name": "test", "description": "test"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_role_forbidden(self, client, user_headers):
        response = await client.post(
            "/api/v1/roles/",
            json={"name": "forbidden_role", "description": "test"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestRoleAPIUpdate:
    async def test_update_role_success(self, client, superuser_headers):
        unique_id = uuid.uuid4().hex[:8]
        create_response = await client.post(
            "/api/v1/roles/",
            json={"name": f"update_role_{unique_id}", "description": "Original"},
            headers=superuser_headers,
        )
        role_id = create_response.json()["data"]["id"]

        response = await client.put(
            f"/api/v1/roles/{role_id}",
            json={"description": "Updated"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["description"] == "Updated"

    async def test_update_role_not_found(self, client, superuser_headers):
        response = await client.put(
            f"/api/v1/roles/{NONEXISTENT_ID}",
            json={"description": "Updated"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_role_forbidden(self, client, user_headers):
        response = await client.put(
            "/api/v1/roles/1",
            json={"description": "Updated"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestRoleAPIDelete:
    async def test_delete_role_success(self, client, superuser_headers):
        unique_id = uuid.uuid4().hex[:8]
        create_response = await client.post(
            "/api/v1/roles/",
            json={"name": f"delete_role_{unique_id}", "description": "To delete"},
            headers=superuser_headers,
        )
        role_id = create_response.json()["data"]["id"]

        response = await client.delete(f"/api/v1/roles/{role_id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_role_not_found(self, client, superuser_headers):
        response = await client.delete(f"/api/v1/roles/{NONEXISTENT_ID}", headers=superuser_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_role_forbidden(self, client, user_headers):
        response = await client.delete("/api/v1/roles/1", headers=user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestRoleAPIAssign:
    async def test_assign_role_to_user_success(self, client, superuser_headers, test_user):
        unique_id = uuid.uuid4().hex[:8]
        create_response = await client.post(
            "/api/v1/roles/",
            json={"name": f"assign_role_{unique_id}", "description": "Assign test"},
            headers=superuser_headers,
        )
        role_id = create_response.json()["data"]["id"]

        response = await client.post(
            "/api/v1/roles/assign",
            json={"user_id": test_user.id, "role_id": role_id},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["user_id"] == test_user.id

    async def test_assign_role_forbidden(self, client, user_headers, test_user):
        response = await client.post(
            "/api/v1/roles/assign",
            json={"user_id": test_user.id, "role_id": 1},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_remove_role_from_user_success(self, client, superuser_headers, test_user):
        unique_id = uuid.uuid4().hex[:8]
        create_response = await client.post(
            "/api/v1/roles/",
            json={"name": f"remove_role_{unique_id}", "description": "Remove test"},
            headers=superuser_headers,
        )
        role_id = create_response.json()["data"]["id"]

        await client.post(
            "/api/v1/roles/assign",
            json={"user_id": test_user.id, "role_id": role_id},
            headers=superuser_headers,
        )

        response = await client.delete(
            f"/api/v1/roles/assign/{test_user.id}/{role_id}",
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_get_user_roles_success(self, client, superuser_headers, test_user):
        response = await client.get(f"/api/v1/roles/users/{test_user.id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "data" in response.json()


@pytest.mark.asyncio
class TestPermissionAPIList:
    async def test_get_permissions_success(self, client, superuser_headers):
        response = await client.get("/api/v1/permissions/", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data

    async def test_get_permissions_unauthorized(self, client):
        response = await client.get("/api/v1/permissions/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestPermissionAPICreate:
    async def test_create_permission_success(self, client, superuser_headers):
        unique_id = uuid.uuid4().hex[:8]
        response = await client.post(
            "/api/v1/permissions/",
            json={"name": f"Test Permission {unique_id}", "code": f"test:api_{unique_id}"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["code"] == f"test:api_{unique_id}"

    async def test_create_permission_unauthorized(self, client):
        response = await client.post(
            "/api/v1/permissions/",
            json={"name": "Test", "code": "test:code"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_permission_forbidden(self, client, user_headers):
        response = await client.post(
            "/api/v1/permissions/",
            json={"name": "Test", "code": "test:code"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestPermissionAPIGetById:
    async def test_get_permission_by_id_success(self, client, superuser_headers):
        unique_id = uuid.uuid4().hex[:8]
        create_response = await client.post(
            "/api/v1/permissions/",
            json={"name": f"Get Permission {unique_id}", "code": f"get:api_{unique_id}"},
            headers=superuser_headers,
        )
        permission_id = create_response.json()["data"]["id"]

        response = await client.get(f"/api/v1/permissions/{permission_id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK

    async def test_get_permission_by_id_not_found(self, client, superuser_headers):
        response = await client.get(f"/api/v1/permissions/{NONEXISTENT_ID}", headers=superuser_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
class TestPermissionAPIUpdate:
    async def test_update_permission_success(self, client, superuser_headers):
        unique_id = uuid.uuid4().hex[:8]
        create_response = await client.post(
            "/api/v1/permissions/",
            json={"name": f"Update Permission {unique_id}", "code": f"update:api_{unique_id}"},
            headers=superuser_headers,
        )
        permission_id = create_response.json()["data"]["id"]

        response = await client.put(
            f"/api/v1/permissions/{permission_id}",
            json={"name": "Updated Permission Name"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
class TestPermissionAPIDelete:
    async def test_delete_permission_success(self, client, superuser_headers):
        unique_id = uuid.uuid4().hex[:8]
        create_response = await client.post(
            "/api/v1/permissions/",
            json={"name": f"Delete Permission {unique_id}", "code": f"delete:api_{unique_id}"},
            headers=superuser_headers,
        )
        permission_id = create_response.json()["data"]["id"]

        response = await client.delete(f"/api/v1/permissions/{permission_id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT
