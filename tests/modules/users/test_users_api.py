import uuid

import pytest
from fastapi import status

from tests.conftest import NONEXISTENT_ID, TEST_PASSWORD
from tests.helpers import register_and_login


@pytest.mark.asyncio
class TestUserRegistration:
    async def test_register_success(self, client):
        uid = uuid.uuid4().hex[:8]
        email = f"test_{uid}@example.com"
        username = f"testuser_{uid}"
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "username": username,
                "full_name": "Test User",
                "password": TEST_PASSWORD,
                "is_active": True,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == email
        assert data["data"]["username"] == username

    async def test_register_duplicate_email(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "username": "user1",
                "password": TEST_PASSWORD,
            },
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "username": "user2",
                "password": TEST_PASSWORD,
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already registered" in data["error"]["message"]

    async def test_register_duplicate_username(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user1@example.com",
                "username": "duplicateuser",
                "password": TEST_PASSWORD,
            },
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user2@example.com",
                "username": "duplicateuser",
                "password": TEST_PASSWORD,
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already taken" in data["error"]["message"]


@pytest.mark.asyncio
class TestPasswordValidation:
    async def test_register_password_too_short(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com",
                "username": "shortpass",
                "password": "short",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_register_password_no_letter(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "nodigit@example.com",
                "username": "nodigit",
                "password": "12345678",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_register_password_no_digit(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "noletter@example.com",
                "username": "noletter",
                "password": "onlyletters",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_register_invalid_email(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "username": "invalidemail",
                "password": TEST_PASSWORD,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
class TestUserLogin:
    async def test_login_success(self, client):
        uid = uuid.uuid4().hex[:8]
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"login_{uid}@example.com",
                "username": f"logintest_{uid}",
                "password": TEST_PASSWORD,
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": f"logintest_{uid}", "password": TEST_PASSWORD},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]

    async def test_login_wrong_password(self, client):
        uid = uuid.uuid4().hex[:8]
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"wrongpass_{uid}@example.com",
                "username": f"wrongpassuser_{uid}",
                "password": "correctpassword123",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": f"wrongpassuser_{uid}", "password": "wrongpassword"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "Invalid credentials" in data["error"]["message"]

    async def test_login_nonexistent_user(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "anypassword"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestTokenValidation:
    async def test_token_format(self, client):
        user_data, _, _ = await register_and_login(client)

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": user_data["username"], "password": TEST_PASSWORD},
        )
        data = login_resp.json()
        token = data["data"]["access_token"]
        token_type = data["data"]["token_type"]

        assert token_type == "bearer"
        assert len(token.split(".")) == 3

    async def test_token_payload_structure(self, client):
        import base64
        import json

        _, token, _ = await register_and_login(client)

        payload_b64 = token.split(".")[1]
        payload_json = base64.urlsafe_b64decode(payload_b64 + "==")
        payload = json.loads(payload_json)

        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload
        assert payload["type"] == "access"


@pytest.mark.asyncio
class TestGetCurrentUser:
    async def test_get_me_success(self, client):
        user_data, _, headers = await register_and_login(client)

        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == user_data["username"]
        assert data["data"]["email"] == user_data["email"]

    async def test_get_me_without_token(self, client):
        response = await client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_me_invalid_token(self, client):
        response = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestGetUserById:
    async def test_get_user_by_id_success(self, client):
        _, _, headers = await register_and_login(client)

        me_response = await client.get("/api/v1/users/me", headers=headers)
        user_id = me_response.json()["data"]["id"]

        response = await client.get(
            f"/api/v1/users/{user_id}",
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == user_id

    async def test_get_user_by_id_not_found(self, client):
        _, _, headers = await register_and_login(client)

        response = await client.get(
            f"/api/v1/users/{NONEXISTENT_ID}",
            headers=headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["error"]["message"].lower()


@pytest.mark.asyncio
class TestUpdateUser:
    async def test_update_own_user_success(self, client):
        user_data, _, headers = await register_and_login(client)

        # Get current user to get the ID
        me_response = await client.get("/api/v1/users/me", headers=headers)
        user_id = me_response.json()["data"]["id"]

        response = await client.put(
            f"/api/v1/users/{user_id}",
            json={"full_name": "Updated Name"},
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["full_name"] == "Updated Name"

    async def test_update_user_forbidden(self, client):
        _, _, headers1 = await register_and_login(client)
        user_data2, _, _ = await register_and_login(client)

        # Get user2's ID
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": user_data2["username"], "password": TEST_PASSWORD},
        )
        token2 = login_resp.json()["data"]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        me_resp = await client.get("/api/v1/users/me", headers=headers2)
        other_user_id = me_resp.json()["data"]["id"]

        response = await client.put(
            f"/api/v1/users/{other_user_id}",
            json={"full_name": "Hacked Name"},
            headers=headers1,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "permissions" in data["error"]["message"].lower()

    async def test_update_duplicate_email(self, client):
        uid = uuid.uuid4().hex[:8]
        # Register first user
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"existing_{uid}@example.com",
                "username": f"existing_{uid}",
                "password": TEST_PASSWORD,
            },
        )
        # Register second user
        user_data2, _, headers2 = await register_and_login(client)
        me_resp = await client.get("/api/v1/users/me", headers=headers2)
        user_id = me_resp.json()["data"]["id"]

        response = await client.put(
            f"/api/v1/users/{user_id}",
            json={"email": f"existing_{uid}@example.com"},
            headers=headers2,
        )
        assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
class TestDeleteUser:
    async def test_delete_user_forbidden(self, client):
        _, _, headers1 = await register_and_login(client)
        user_data2, _, _ = await register_and_login(client)

        # Get user2's ID
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": user_data2["username"], "password": TEST_PASSWORD},
        )
        token2 = login_resp.json()["data"]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        me_resp = await client.get("/api/v1/users/me", headers=headers2)
        other_user_id = me_resp.json()["data"]["id"]

        response = await client.delete(
            f"/api/v1/users/{other_user_id}",
            headers=headers1,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestErrorResponse:
    async def test_unauthorized_response_format(self, client):
        response = await client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        # FastAPI's OAuth2PasswordBearer returns {"detail": "Not authenticated"} when no token
        assert "detail" in data

    async def test_not_found_response_format(self, client):
        _, _, headers = await register_and_login(client)

        response = await client.get(
            f"/api/v1/users/{NONEXISTENT_ID}",
            headers=headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert "message" in data["error"]


@pytest.mark.asyncio
class TestHealthCheck:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    async def test_readiness_check(self, client):
        response = await client.get("/health/ready")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] in ["ready", "degraded"]
        assert "databases" in data
        assert "user_db" in data["databases"]
        assert "business_db" in data["databases"]
        assert "config_db" in data["databases"]

    async def test_root_endpoint(self, client):
        response = await client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "Enterprise FastAPI" in data["message"]
        assert "docs" in data
