import pytest
from fastapi import status


@pytest.mark.asyncio
class TestUserRegistration:
    async def test_register_success(self, client):
        response = await client.post(
            "/api/v1/users/register",
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
            "/api/v1/users/register",
            json={
                "email": "duplicate@example.com",
                "username": "user1",
                "password": "testpassword123",
            },
        )
        response = await client.post(
            "/api/v1/users/register",
            json={
                "email": "duplicate@example.com",
                "username": "user2",
                "password": "testpassword123",
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
class TestUserLogin:
    async def test_login_success(self, client):
        await client.post(
            "/api/v1/users/register",
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


class TestHealthCheck:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
