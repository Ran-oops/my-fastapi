import pytest
from fastapi import status


@pytest.mark.asyncio
class TestUserRegistration:
    async def test_register_success(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "full_name": "Test User",
                "password": "testpassword123",
                "is_active": True,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == "test@example.com"
        assert data["data"]["username"] == "testuser"

    async def test_register_duplicate_email(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "username": "user1",
                "password": "testpassword123",
            },
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "username": "user2",
                "password": "testpassword123",
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_register_duplicate_username(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user1@example.com",
                "username": "duplicateuser",
                "password": "testpassword123",
            },
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user2@example.com",
                "username": "duplicateuser",
                "password": "testpassword123",
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
class TestUserLogin:
    async def test_login_success(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "username": "logintest",
                "password": "testpassword123",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "logintest", "password": "testpassword123"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]

    async def test_login_wrong_password(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongpass@example.com",
                "username": "wrongpassuser",
                "password": "correctpassword123",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "wrongpassuser", "password": "wrongpassword"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_login_nonexistent_user(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "anypassword"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
class TestGetCurrentUser:
    async def test_get_me_success(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "me@example.com",
                "username": "meuser",
                "password": "testpassword123",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "meuser", "password": "testpassword123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = await client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == "meuser"
        assert data["data"]["email"] == "me@example.com"

    async def test_get_me_without_token(self, client):
        response = await client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_me_invalid_token(self, client):
        response = await client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestGetUserById:
    async def test_get_user_by_id_success(self, client):
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "getbyid@example.com",
                "username": "getbyiduser",
                "password": "testpassword123",
            },
        )
        user_id = register_response.json()["data"]["id"]

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "getbyiduser", "password": "testpassword123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = await client.get(
            f"/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == user_id

    async def test_get_user_by_id_not_found(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "notfound@example.com",
                "username": "notfounduser",
                "password": "testpassword123",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "notfounduser", "password": "testpassword123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = await client.get(
            "/api/v1/users/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
class TestUpdateUser:
    async def test_update_own_user_success(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "update@example.com",
                "username": "updateuser",
                "password": "testpassword123",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "updateuser", "password": "testpassword123"},
        )
        token = login_response.json()["data"]["access_token"]
        user_id = login_response.json().get("data", {}).get("user_id")

        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "update2@example.com",
                "username": "updateuser2",
                "password": "testpassword123",
            },
        )
        user_id = register_response.json()["data"]["id"]

        response = await client.put(
            f"/api/v1/users/{user_id}",
            json={"full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["full_name"] == "Updated Name"

    async def test_update_user_forbidden(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "forbidden1@example.com",
                "username": "forbidden1",
                "password": "testpassword123",
            },
        )
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "forbidden2@example.com",
                "username": "forbidden2",
                "password": "testpassword123",
            },
        )
        other_user_id = register_response.json()["data"]["id"]

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "forbidden1", "password": "testpassword123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = await client.put(
            f"/api/v1/users/{other_user_id}",
            json={"full_name": "Hacked Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestDeleteUser:
    async def test_delete_user_forbidden(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "delete1@example.com",
                "username": "delete1",
                "password": "testpassword123",
            },
        )
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "delete2@example.com",
                "username": "delete2",
                "password": "testpassword123",
            },
        )
        other_user_id = register_response.json()["data"]["id"]

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "delete1", "password": "testpassword123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = await client.delete(
            f"/api/v1/users/{other_user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestHealthCheck:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
