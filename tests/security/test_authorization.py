"""Security tests for authorization mechanisms.

Tests for:
- Horizontal privilege escalation
- Vertical privilege escalation
- Access to non-existent resources
- Private data leakage
"""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, create_refresh_token


class TestHorizontalPrivilegeEscalation:
    """Test horizontal privilege escalation (accessing other users' data)."""

    async def test_user_cannot_access_other_user_data(self, client, test_user, session):
        """Test regular user cannot access another user's data."""
        import uuid

        from app.core.security import get_password_hash
        from app.modules.users.models import User

        # Create another user
        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password=get_password_hash("password123"),
            full_name="Other User",
            is_active=True,
            is_superuser=False,
        )
        session.add(other_user)
        await session.commit()
        await session.refresh(other_user)

        # Create token for first user
        token = create_access_token(str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # Try to access other user's data
        response = await client.get(f"/api/v1/users/{other_user.id}", headers=headers)
        # Depending on implementation, could be 404 or 403
        assert response.status_code in [403, 404]

    async def test_user_cannot_update_other_user_data(self, client, test_user, session):
        """Test regular user cannot update another user's data."""
        import uuid

        from app.core.security import get_password_hash
        from app.modules.users.models import User

        # Create another user
        other_user = User(
            email="other2@example.com",
            username="otheruser2",
            hashed_password=get_password_hash("password123"),
            full_name="Other User",
            is_active=True,
            is_superuser=False,
        )
        session.add(other_user)
        await session.commit()
        await session.refresh(other_user)

        # Create token for first user
        token = create_access_token(str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # Try to update other user's data
        response = await client.put(
            f"/api/v1/users/{other_user.id}",
            json={"full_name": "Hacked Name"},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_user_cannot_delete_other_user(self, client, test_user, session):
        """Test regular user cannot delete another user."""
        import uuid

        from app.core.security import get_password_hash
        from app.modules.users.models import User

        # Create another user
        other_user = User(
            email="other3@example.com",
            username="otheruser3",
            hashed_password=get_password_hash("password123"),
            full_name="Other User",
            is_active=True,
            is_superuser=False,
        )
        session.add(other_user)
        await session.commit()
        await session.refresh(other_user)

        # Create token for first user
        token = create_access_token(str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # Try to delete other user
        response = await client.delete(f"/api/v1/users/{other_user.id}", headers=headers)
        assert response.status_code == 403

    async def test_user_can_access_own_data(self, client, test_user):
        """Test user can access their own data."""
        token = create_access_token(str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == test_user.id

    async def test_user_can_update_own_data(self, client, test_user):
        """Test user can update their own data."""
        token = create_access_token(str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.put(
            f"/api/v1/users/{test_user.id}",
            json={"full_name": "Updated Name"},
            headers=headers,
        )
        assert response.status_code == 200


class TestVerticalPrivilegeEscalation:
    """Test vertical privilege escalation (gaining higher privileges)."""

    async def test_regular_user_cannot_access_admin_endpoints(self, client, test_user):
        """Test regular user cannot access admin-only endpoints."""
        token = create_access_token(str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # Try to access admin endpoint (list all users)
        response = await client.get("/api/v1/users/", headers=headers)
        assert response.status_code == 403

    async def test_user_cannot_escalate_to_superuser(self, client, test_user, session):
        """Test user cannot escalate their own privileges."""
        token = create_access_token(str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # Try to set is_superuser to true
        response = await client.put(
            f"/api/v1/users/{test_user.id}",
            json={"is_superuser": True},
            headers=headers,
        )
        # Should either be rejected or field ignored
        assert response.status_code in [200, 400, 403, 422]

        if response.status_code == 200:
            # Verify user is still not superuser
            data = response.json()
            assert data["data"]["is_superuser"] is False

    async def test_superuser_can_access_admin_endpoints(self, client, test_superuser):
        """Test superuser can access admin endpoints."""
        token = create_access_token(str(test_superuser.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users/", headers=headers)
        assert response.status_code == 200

    async def test_invalid_token_format_rejected(self, client):
        """Test invalid token formats are rejected."""
        invalid_headers = [
            {"Authorization": "Bearer "},  # Empty token
            {"Authorization": "Bearer invalid_token"},  # Malformed token
            {"Authorization": "Basic dXNlcjpwYXNz"},  # Basic auth
            {"Authorization": "Token invalid"},  # Wrong scheme
            {"X-Custom-Auth": "Bearer token"},  # Wrong header
        ]

        for headers in invalid_headers:
            response = await client.get("/api/v1/users/me", headers=headers)
            assert response.status_code in [401, 403]

    async def test_missing_authorization_header(self, client):
        """Test missing authorization header is rejected."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401


class TestNonExistentResourceAccess:
    """Test access to non-existent resources."""

    async def test_access_nonexistent_user(self, client, test_superuser):
        """Test accessing non-existent user returns 404."""
        token = create_access_token(str(test_superuser.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users/99999", headers=headers)
        assert response.status_code == 404

    async def test_update_nonexistent_user(self, client, test_superuser):
        """Test updating non-existent user returns 404."""
        token = create_access_token(str(test_superuser.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.put(
            "/api/v1/users/99999",
            json={"full_name": "Test"},
            headers=headers,
        )
        assert response.status_code == 404

    async def test_delete_nonexistent_user(self, client, test_superuser):
        """Test deleting non-existent user returns 404."""
        token = create_access_token(str(test_superuser.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.delete("/api/v1/users/99999", headers=headers)
        assert response.status_code == 404

    async def test_negative_id_rejected(self, client, test_superuser):
        """Test negative IDs are rejected."""
        token = create_access_token(str(test_superuser.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users/-1", headers=headers)
        # Should be 404 or 400
        assert response.status_code in [400, 404, 422]

    async def test_zero_id_handling(self, client, test_superuser):
        """Test ID of zero is handled."""
        token = create_access_token(str(test_superuser.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users/0", headers=headers)
        assert response.status_code in [404, 400, 422]

    async def test_string_id_rejected(self, client, test_superuser):
        """Test string IDs are rejected."""
        token = create_access_token(str(test_superuser.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users/abc", headers=headers)
        assert response.status_code in [400, 422]

    async def test_sql_injection_in_resource_id(self, client, test_superuser):
        """Test SQL injection in resource ID is prevented."""
        token = create_access_token(str(test_superuser.id))
        headers = {"Authorization": f"Bearer {token}"}

        injection_attempts = [
            "1 OR 1=1",
            "1; DROP TABLE users;--",
            "' OR '1'='1",
            "1 UNION SELECT * FROM users",
        ]

        for injection in injection_attempts:
            response = await client.get(f"/api/v1/users/{injection}", headers=headers)
            # Should return 404, 400, or 422, not 500 or success
            assert response.status_code in [400, 404, 422]


class TestPrivateDataLeakage:
    """Test prevention of private data leakage."""

    async def test_user_data_does_not_expose_password_hash(self, client, test_user):
        """Test user data doesn't expose password hash."""
        token = create_access_token(str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Should not contain password-related fields
        assert "password" not in str(data).lower()
        assert "hashed_password" not in str(data).lower()
        assert "hash" not in str(data).lower()

    async def test_list_users_does_not_expose_sensitive_data(self, client, test_superuser, session):
        """Test user listing doesn't expose sensitive data."""
        import uuid

        from app.core.security import get_password_hash
        from app.modules.users.models import User

        # Create test user
        user = User(
            email="leaktest@example.com",
            username="leaktest",
            hashed_password=get_password_hash("password123"),
            full_name="Leak Test",
            is_active=True,
            is_superuser=False,
        )
        session.add(user)
        await session.commit()

        token = create_access_token(str(test_superuser.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users/", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Check all users in the list
        for user_data in data.get("data", []):
            assert "password" not in str(user_data).lower()
            assert "hashed_password" not in str(user_data).lower()

    async def test_error_messages_do_not_leak_internal_details(self, client):
        """Test error messages don't leak internal implementation details."""
        # Trigger various errors
        test_cases = [
            ("/api/v1/users/99999", 404),
            ("/api/v1/users/invalid", 422),
        ]

        for endpoint, _ in test_cases:
            response = await client.get(endpoint)
            data = response.json()

            # Check for internal details in error message
            error_str = str(data).lower()
            sensitive_keywords = [
                "sql",
                "database",
                "exception",
                "traceback",
                "internal server error",
                "password",
                "secret",
                "key",
            ]

            for keyword in sensitive_keywords:
                assert keyword not in error_str, f"Sensitive info leaked: {keyword}"

    async def test_api_does_not_expose_internal_paths(self, client):
        """Test API doesn't expose internal file paths."""
        # Try to access common internal paths
        internal_paths = [
            "/.env",
            "/.git",
            "/config.py",
            "/settings.py",
            "/requirements.txt",
            "/Dockerfile",
        ]

        for path in internal_paths:
            response = await client.get(path)
            # Should return 404
            assert response.status_code == 404

    async def test_stack_trace_not_exposed(self, client):
        """Test stack traces are not exposed in production mode."""
        # This would need to run in production-like mode
        # For now, just verify error responses are JSON
        response = await client.get("/api/v1/users/99999")
        data = response.json()

        # Response should be valid JSON
        assert isinstance(data, dict)

    async def test_authentication_error_generic_message(self, client, test_user):
        """Test authentication errors use generic messages."""
        # Try login with wrong password
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": test_user.username, "password": "wrongpassword"},
        )

        assert response.status_code == 401
        data = response.json()

        # Error message should be generic
        error_msg = str(data.get("error", {}).get("message", "")).lower()
        assert "password" in error_msg or "credentials" in error_msg or "invalid" in error_msg

    async def test_token_payload_minimal_exposure(self, client, test_user):
        """Test JWT token payload doesn't expose sensitive data."""
        from jose import jwt

        from app.core.config import settings
        from app.core.security import ALGORITHM

        token = create_access_token(str(test_user.id))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

        # Payload should only contain necessary claims
        allowed_claims = {"sub", "exp", "iat", "type"}
        assert set(payload.keys()) <= allowed_claims

        # Should not contain sensitive data
        assert "password" not in str(payload).lower()
        assert "email" not in str(payload).lower()
        assert "username" not in str(payload).lower()


class TestAuthorizationEdgeCases:
    """Test authorization edge cases."""

    async def test_inactive_user_cannot_access(self, client, session):
        """Test inactive users cannot access protected resources."""
        import uuid

        from app.core.security import get_password_hash
        from app.modules.users.models import User

        # Create inactive user
        inactive_user = User(
            email="inactive@example.com",
            username="inactiveuser",
            hashed_password=get_password_hash("password123"),
            full_name="Inactive User",
            is_active=False,
            is_superuser=False,
        )
        session.add(inactive_user)
        await session.commit()
        await session.refresh(inactive_user)

        # Create token for inactive user
        token = create_access_token(str(inactive_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

    async def test_deleted_user_token_rejected(self, client, test_user, session):
        """Test tokens for deleted users are rejected."""
        from app.modules.users.repository import user_repo

        # Delete user
        await user_repo.delete(session, id=test_user.id)

        # Try to use token
        token = create_access_token(str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code in [401, 404]

    async def test_expired_token_rejected(self, client, test_user):
        """Test expired tokens are rejected for authorization."""
        from datetime import UTC, datetime, timedelta

        from jose import jwt

        from app.core.config import settings
        from app.core.security import ALGORITHM

        # Create expired token
        expired_token = jwt.encode(
            {
                "sub": str(test_user.id),
                "type": "access",
                "exp": datetime.now(UTC) - timedelta(minutes=5),
                "iat": datetime.now(UTC) - timedelta(minutes=10),
            },
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

    async def test_concurrent_requests_with_same_token(self, client, test_user):
        """Test concurrent requests with same token."""
        import asyncio

        token = create_access_token(str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # Make multiple concurrent requests
        tasks = [client.get("/api/v1/users/me", headers=headers) for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200

    async def test_token_reuse_after_logout(self, client, test_user):
        """Test token behavior after logout (if implemented)."""
        token = create_access_token(str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # First request should work
        response1 = await client.get("/api/v1/users/me", headers=headers)
        assert response1.status_code == 200

        # If there's no logout endpoint, token should still work
        # This test documents expected behavior
        response2 = await client.get("/api/v1/users/me", headers=headers)
        # Token should still be valid (no blacklist mechanism in basic implementation)
        assert response2.status_code == 200
