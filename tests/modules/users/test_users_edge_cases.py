"""
Edge cases and boundary condition tests for users module.

Tests cover:
- Boundary value testing (min/max values, boundary values)
- Exception inputs (None, empty strings, special characters)
- Concurrency scenarios
- Resource contention
- State machine invalid transitions
"""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import status

from app.core.security import create_access_token, verify_token
from tests.conftest import NONEXISTENT_ID, TEST_PASSWORD
from tests.helpers import register_and_login


@pytest.mark.asyncio
class TestUsernameEdgeCases:
    """Tests for username boundary conditions and edge cases."""

    async def test_username_minimum_length(self, client):
        """Test username at minimum boundary (1 character)."""
        uid = uuid.uuid4().hex[:8]
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"minuser_{uid}@example.com",
                "username": "a",  # Single character
                "password": TEST_PASSWORD,
            },
        )
        # Should succeed - no min length constraint in schema
        assert response.status_code == status.HTTP_201_CREATED

    async def test_username_maximum_length(self, client):
        """Test very long username (100+ characters)."""
        uid = uuid.uuid4().hex[:8]
        long_username = "a" * 150
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"maxuser_{uid}@example.com",
                "username": long_username,
                "password": TEST_PASSWORD,
            },
        )
        # May succeed or fail depending on DB constraints
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_CONTENT]

    async def test_username_special_characters(self, client):
        """Test username with special characters."""
        uid = uuid.uuid4().hex[:8]
        special_usernames = [
            f"user_{uid}!@#$%",  # Special chars
            f"user_{uid}<script>",  # HTML tags
            f"user_{uid}'; DROP TABLE users; --",  # SQL injection attempt
            f"user_{uid}\n\t\r",  # Whitespace control chars
            f"user_{uid}日本語",  # Unicode
            f"user_{uid}🔥emoji",  # Emoji
        ]

        for username in special_usernames:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"{uuid.uuid4().hex[:8]}@example.com",
                    "username": username,
                    "password": TEST_PASSWORD,
                },
            )
            # Should either create or reject, not crash
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                status.HTTP_400_BAD_REQUEST,
            ]

    async def test_username_empty_string(self, client):
        """Test empty username."""
        uid = uuid.uuid4().hex[:8]
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"empty_{uid}@example.com",
                "username": "",
                "password": TEST_PASSWORD,
            },
        )
        # Empty string should be rejected
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_username_whitespace_only(self, client):
        """Test username with only whitespace."""
        uid = uuid.uuid4().hex[:8]
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"whitespace_{uid}@example.com",
                "username": "   ",
                "password": TEST_PASSWORD,
            },
        )
        # Whitespace-only should be rejected
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_username_null_value(self, client):
        """Test null username."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "null@example.com",
                "username": None,
                "password": TEST_PASSWORD,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
class TestEmailEdgeCases:
    """Tests for email boundary conditions and edge cases."""

    async def test_email_maximum_length(self, client):
        """Test very long email address."""
        uid = uuid.uuid4().hex[:8]
        local_part = "a" * 200
        long_email = f"{local_part}@example.com"
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": long_email,
                "username": f"longemail_{uid}",
                "password": TEST_PASSWORD,
            },
        )
        # May succeed or fail depending on validation
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ]

    async def test_email_special_characters_in_local(self, client):
        """Test email with special characters in local part."""
        uid = uuid.uuid4().hex[:8]
        special_emails = [
            f"user+tag_{uid}@example.com",  # Plus sign
            f"user.name_{uid}@example.com",  # Dot in local
            f"user_name_{uid}@example.com",  # Underscore
            f"user-name_{uid}@example.com",  # Hyphen
        ]

        for email in special_emails:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "username": f"spec_{uuid.uuid4().hex[:6]}",
                    "password": TEST_PASSWORD,
                },
            )
            # Valid email formats should succeed
            assert response.status_code == status.HTTP_201_CREATED

    async def test_email_invalid_formats(self, client):
        """Test various invalid email formats."""
        uid = uuid.uuid4().hex[:8]
        invalid_emails = [
            "notanemail",
            "@example.com",  # Missing local
            f"user_{uid}@",  # Missing domain
            f"user_{uid}@.com",  # Dot at domain start
            f"user_{uid}@com",  # No TLD
            f"user_{uid}@exam ple.com",  # Space in domain
            f"user@{uid}@example.com",  # Multiple @
            "",  # Empty
        ]

        for email in invalid_emails:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "username": f"invalid_{uuid.uuid4().hex[:6]}",
                    "password": TEST_PASSWORD,
                },
            )
            # All should be rejected
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_email_null_value(self, client):
        """Test null email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": None,
                "username": f"nullemail_{uuid.uuid4().hex[:8]}",
                "password": TEST_PASSWORD,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_email_case_sensitivity(self, client):
        """Test email case handling."""
        uid = uuid.uuid4().hex[:8]
        base_email = f"CaseTest_{uid}@Example.COM"

        # Register with mixed case
        response1 = await client.post(
            "/api/v1/auth/register",
            json={
                "email": base_email,
                "username": f"case1_{uid}",
                "password": TEST_PASSWORD,
            },
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to register with different case
        response2 = await client.post(
            "/api/v1/auth/register",
            json={
                "email": base_email.lower(),
                "username": f"case2_{uid}",
                "password": TEST_PASSWORD,
            },
        )
        # Should be rejected as duplicate (case insensitive)
        assert response2.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
class TestPasswordBoundaryCases:
    """Tests for password boundary conditions."""

    async def test_password_exactly_8_characters(self, client):
        """Test password at minimum boundary (8 chars)."""
        uid = uuid.uuid4().hex[:8]
        password = "A1" + "b" * 6  # Exactly 8 chars with letter and digit
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"minpass_{uid}@example.com",
                "username": f"minpass_{uid}",
                "password": password,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_password_exactly_72_characters(self, client):
        """Test password at maximum boundary (72 chars - bcrypt limit)."""
        uid = uuid.uuid4().hex[:8]
        # 72 chars: need letter, digit, rest can be anything
        password = "A1" + "b" * 70  # Exactly 72 chars
        assert len(password) == 72
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"maxpass_{uid}@example.com",
                "username": f"maxpass_{uid}",
                "password": password,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_password_73_characters_rejected(self, client):
        """Test password exceeding 72 chars is rejected."""
        uid = uuid.uuid4().hex[:8]
        password = "A1" + "b" * 71  # 73 chars
        assert len(password) == 73
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"toobig_{uid}@example.com",
                "username": f"toobig_{uid}",
                "password": password,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_password_71_characters_accepted(self, client):
        """Test password at 71 chars is accepted."""
        uid = uuid.uuid4().hex[:8]
        password = "A1" + "b" * 69  # 71 chars
        assert len(password) == 71
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"pass71_{uid}@example.com",
                "username": f"pass71_{uid}",
                "password": password,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_password_empty_string(self, client):
        """Test empty password."""
        uid = uuid.uuid4().hex[:8]
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"emptypass_{uid}@example.com",
                "username": f"emptypass_{uid}",
                "password": "",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_password_only_letters(self, client):
        """Test password with only letters (no digits)."""
        uid = uuid.uuid4().hex[:8]
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"nodigit_{uid}@example.com",
                "username": f"nodigit_{uid}",
                "password": "onlyletters",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_password_only_digits(self, client):
        """Test password with only digits (no letters)."""
        uid = uuid.uuid4().hex[:8]
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"noletter_{uid}@example.com",
                "username": f"noletter_{uid}",
                "password": "12345678",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_password_7_characters_rejected(self, client):
        """Test password at 7 chars (below minimum) is rejected."""
        uid = uuid.uuid4().hex[:8]
        password = "A1bcdef"  # 7 chars
        assert len(password) == 7
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"pass7_{uid}@example.com",
                "username": f"pass7_{uid}",
                "password": password,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
class TestConcurrentUserCreation:
    """Tests for concurrent user creation scenarios."""

    async def test_concurrent_registration_same_username(self, client):
        """Test concurrent registration attempts with same username."""
        uid = uuid.uuid4().hex[:8]
        username = f"concurrent_{uid}"

        async def register_attempt(email_suffix):
            return await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"concurrent_{email_suffix}_{uid}@example.com",
                    "username": username,
                    "password": TEST_PASSWORD,
                },
            )

        # Launch multiple concurrent requests
        tasks = [register_attempt(i) for i in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        success_count = sum(1 for r in responses if isinstance(r, type(await client.get("/"))) and r.status_code == 201)
        conflict_count = sum(
            1 for r in responses if isinstance(r, type(await client.get("/"))) and r.status_code == 409
        )

        # Only one should succeed, others should get conflict
        assert success_count == 1
        assert conflict_count == 4

    async def test_concurrent_registration_same_email(self, client):
        """Test concurrent registration attempts with same email."""
        uid = uuid.uuid4().hex[:8]
        email = f"concurrent_email_{uid}@example.com"

        async def register_attempt(username_suffix):
            return await client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "username": f"conuser_{username_suffix}_{uid}",
                    "password": TEST_PASSWORD,
                },
            )

        # Launch multiple concurrent requests
        tasks = [register_attempt(i) for i in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        success_count = sum(1 for r in responses if isinstance(r, type(await client.get("/"))) and r.status_code == 201)
        conflict_count = sum(
            1 for r in responses if isinstance(r, type(await client.get("/"))) and r.status_code == 409
        )

        # Only one should succeed, others should get conflict
        assert success_count == 1
        assert conflict_count == 4


@pytest.mark.asyncio
class TestDeletedUserOperations:
    """Tests for operations on deleted users."""

    async def test_login_after_user_deleted(self, client, session):
        """Test login attempt after user is deleted."""
        from app.modules.users.models import User

        # Register and login
        user_data, _, headers = await register_and_login(client)

        # Get user ID
        me_resp = await client.get("/api/v1/users/me", headers=headers)
        user_id = me_resp.json()["data"]["id"]

        # Delete user directly from DB (simulating admin deletion)
        from sqlalchemy import delete

        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()

        # Try to login with deleted user credentials
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": user_data["username"], "password": TEST_PASSWORD},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_access_protected_endpoint_with_deleted_user_token(self, client, session):
        """Test using token of a deleted user."""
        from app.modules.users.models import User
        from sqlalchemy import delete

        # Register and get token
        user_data, token, _ = await register_and_login(client)

        # Get user ID from token
        user_id = verify_token(token)

        # Delete user
        await session.execute(delete(User).where(User.id == int(user_id)))
        await session.commit()

        # Try to access protected endpoint
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should fail since user no longer exists
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]


@pytest.mark.asyncio
class TestInvalidJWTTokenFormats:
    """Tests for invalid JWT token handling."""

    async def test_token_with_wrong_number_of_parts(self, client):
        """Test token with wrong number of base64 parts."""
        invalid_tokens = [
            "invalid",  # One part
            "header.payload",  # Two parts
            "header.payload.signature.extra",  # Four parts
            "",  # Empty
        ]

        for token in invalid_tokens:
            response = await client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_with_invalid_base64(self, client):
        """Test token with invalid base64 encoding."""
        # Valid structure but invalid base64
        invalid_token = "!!!.!!!.!!!"
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_with_valid_format_wrong_secret(self, client):
        """Test token with valid format but wrong signature."""
        import base64
        import json

        # Create a token with wrong secret
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        payload = (
            base64.urlsafe_b64encode(json.dumps({"sub": "99999", "exp": 9999999999}).encode()).decode().rstrip("=")
        )
        fake_signature = base64.urlsafe_b64encode(b"fake_signature").decode().rstrip("=")

        fake_token = f"{header}.{payload}.{fake_signature}"

        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {fake_token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_with_expired_timestamp(self, client):
        """Test expired token."""
        # Create a token that expired in the past
        expired_token = create_access_token(subject="99999", expires_delta=__import__("datetime").timedelta(minutes=-1))

        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_without_authorization_header(self, client):
        """Test request without Authorization header."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_with_wrong_prefix(self, client, user_token):
        """Test token with wrong prefix (not 'Bearer')."""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Basic {user_token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_with_only_bearer_no_token(self, client):
        """Test Authorization header with only 'Bearer' and no token."""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestUserUpdateEdgeCases:
    """Tests for user update edge cases."""

    async def test_update_to_existing_email(self, client):
        """Test updating user email to one that already exists."""
        # Register two users
        uid1 = uuid.uuid4().hex[:8]
        email1 = f"existing_{uid1}@example.com"

        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email1,
                "username": f"user1_{uid1}",
                "password": TEST_PASSWORD,
            },
        )

        user_data2, _, headers2 = await register_and_login(client)
        me_resp = await client.get("/api/v1/users/me", headers=headers2)
        user_id = me_resp.json()["data"]["id"]

        # Try to update to existing email
        response = await client.put(
            f"/api/v1/users/{user_id}",
            json={"email": email1},
            headers=headers2,
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_update_with_same_email(self, client):
        """Test updating user with same email (should succeed)."""
        user_data, _, headers = await register_and_login(client)
        me_resp = await client.get("/api/v1/users/me", headers=headers)
        user_id = me_resp.json()["data"]["id"]

        response = await client.put(
            f"/api/v1/users/{user_id}",
            json={"email": user_data["email"]},
            headers=headers,
        )
        # Should succeed - no change needed
        assert response.status_code == status.HTTP_200_OK

    async def test_update_full_name_empty_string(self, client):
        """Test updating full_name to empty string."""
        _, _, headers = await register_and_login(client)
        me_resp = await client.get("/api/v1/users/me", headers=headers)
        user_id = me_resp.json()["data"]["id"]

        response = await client.put(
            f"/api/v1/users/{user_id}",
            json={"full_name": ""},
            headers=headers,
        )
        # Should be accepted (setting to empty/null)
        assert response.status_code == status.HTTP_200_OK

    async def test_update_with_null_values(self, client):
        """Test update with null values in optional fields."""
        _, _, headers = await register_and_login(client)
        me_resp = await client.get("/api/v1/users/me", headers=headers)
        user_id = me_resp.json()["data"]["id"]

        response = await client.put(
            f"/api/v1/users/{user_id}",
            json={"full_name": None},
            headers=headers,
        )
        # Should be accepted
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
class TestUserStateTransitions:
    """Tests for user state transitions."""

    async def test_inactive_user_cannot_login(self, client, session):
        """Test that inactive user cannot login."""
        from app.modules.users.models import User

        # Register user
        uid = uuid.uuid4().hex[:8]
        username = f"inactive_{uid}"

        await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{username}@example.com",
                "username": username,
                "password": TEST_PASSWORD,
                "is_active": True,
            },
        )

        # Get user and set inactive
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one()
        user.is_active = False
        await session.commit()

        # Try to login
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": TEST_PASSWORD},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Inactive" in response.json()["error"]["message"]

    async def test_superuser_flag_cannot_be_set_via_api(self, client):
        """Test that regular users cannot set superuser flag via API."""
        uid = uuid.uuid4().hex[:8]
        username = f"trysuper_{uid}"

        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{username}@example.com",
                "username": username,
                "password": TEST_PASSWORD,
                "is_superuser": True,  # Try to set superuser
            },
        )
        # Registration should succeed but superuser flag should be ignored
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["is_superuser"] is False
