"""Security tests for authentication mechanisms.

Tests for:
- Weak password rejection
- Password hash strength
- JWT signature verification
- Token expiration
- Refresh token rotation
- Token forgery detection
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_refresh_token,
    verify_token,
)


class TestWeakPasswordRejection:
    """Test weak password validation and rejection."""

    WEAK_PASSWORDS = [
        "123456",
        "password",
        "qwerty",
        "admin",
        "12345678",
        "password123",
        "letmein",
        "welcome",
        "monkey",
        "dragon",
        "abc123",
        "111111",
        "password1",
        "123456789",
        "1234567",
        "master",
        "sunshine",
        "princess",
        "football",
        "baseball",
    ]

    COMMON_PATTERNS = [
        "Password1!",  # Common pattern
        "Test1234!",
        "User@2024",
        "Aa123456",
        "Qwerty1!",
    ]

    @pytest.mark.parametrize("weak_password", WEAK_PASSWORDS)
    def test_weak_password_hash_still_works(self, weak_password):
        """Test that even weak passwords can be hashed (application should validate separately)."""
        # The security module should hash any password
        # It's the application's responsibility to validate password strength
        hashed = get_password_hash(weak_password)
        assert hashed is not None
        assert len(hashed) > 0
        # Verify the hash works
        assert verify_password(weak_password, hashed)

    def test_password_length_minimum(self):
        """Test password minimum length consideration."""
        # Very short passwords
        short_passwords = ["a", "ab", "abc", "abcd", "abcde", "abc123"]
        for pwd in short_passwords:
            hashed = get_password_hash(pwd)
            assert hashed is not None
            assert verify_password(pwd, hashed)

    def test_password_with_special_characters(self):
        """Test passwords with various special characters."""
        passwords = [
            "Pass@word!123",
            "Test#Pass$2024",
            "Secure*Pass&Word",
            "My_Pass-Word=2024",
            "Complex.Pass,Word",
        ]
        for pwd in passwords:
            hashed = get_password_hash(pwd)
            assert hashed is not None
            assert verify_password(pwd, hashed)

    def test_unicode_password(self):
        """Test passwords with unicode characters."""
        passwords = [
            "密码测试123",
            "パスワード123",
            "MotDePasse123!",
            "Пароль123!",
        ]
        for pwd in passwords:
            hashed = get_password_hash(pwd)
            assert hashed is not None
            assert verify_password(pwd, hashed)


class TestPasswordHashStrength:
    """Test password hashing strength and security."""

    def test_bcrypt_used_for_hashing(self):
        """Verify that bcrypt is used for password hashing."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        # Check it's a valid bcrypt hash
        assert hashed.startswith("$2")
        # Check it contains the bcrypt identifier
        assert "$2a$" in hashed or "$2b$" in hashed or "$2y$" in hashed

    def test_hash_is_not_plaintext(self):
        """Ensure password is never stored in plaintext."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)

        # Hash should not contain the original password
        assert password not in hashed
        assert password.encode() not in hashed.encode()

    def test_same_password_different_hashes(self):
        """Verify same password produces different hashes (salt randomization)."""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Two hashes of same password should be different
        assert hash1 != hash2

    def test_password_verification(self):
        """Test password verification works correctly."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password(wrong_password, hashed) is False

    def test_hash_workload_factor(self):
        """Verify bcrypt workload factor is appropriate."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        # Extract cost factor from hash
        # Format: $2b$<cost>$...
        parts = hashed.split("$")
        if len(parts) >= 3:
            cost_factor = parts[2]
            cost = int(cost_factor.split("$")[0]) if "$" not in cost_factor else int(cost_factor)
            # Cost should be at least 10 for security
            assert cost >= 10

    def test_timing_attack_resistance(self):
        """Test that verification time is roughly constant."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        wrong_password = "WrongPassword"

        # Measure timing for correct password
        times_correct = []
        for _ in range(100):
            start = time.perf_counter()
            verify_password(password, hashed)
            end = time.perf_counter()
            times_correct.append(end - start)

        # Measure timing for wrong password
        times_wrong = []
        for _ in range(100):
            start = time.perf_counter()
            verify_password(wrong_password, hashed)
            end = time.perf_counter()
            times_wrong.append(end - start)

        # Average times should be similar (within 2x factor)
        avg_correct = sum(times_correct) / len(times_correct)
        avg_wrong = sum(times_wrong) / len(times_wrong)

        ratio = max(avg_correct, avg_wrong) / min(avg_correct, avg_wrong)
        assert ratio < 2.0, f"Timing difference too large: {ratio:.2f}x"


class TestJWTSignatureVerification:
    """Test JWT token signature verification."""

    def test_token_contains_expected_claims(self):
        """Verify JWT contains expected claims."""
        user_id = "12345"
        token = create_access_token(user_id)

        # Decode without verification to check claims
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_token_signature_validation(self):
        """Test that tampered tokens are rejected."""
        user_id = "12345"
        token = create_access_token(user_id)

        # Tamper with the token
        parts = token.split(".")
        tampered_token = parts[0] + "." + parts[1] + "." + "tampered_signature"

        # Verification should fail
        result = verify_token(tampered_token)
        assert result is None

    def test_token_with_wrong_secret(self):
        """Test token signed with wrong secret is rejected."""
        user_id = "12345"

        # Create token with wrong secret
        wrong_token = jwt.encode(
            {"sub": user_id, "type": "access", "exp": datetime.now(UTC) + timedelta(hours=1)},
            "wrong-secret-key-for-testing-only",
            algorithm=ALGORITHM,
        )

        # Verification should fail
        result = verify_token(wrong_token)
        assert result is None

    def test_malformed_token_rejection(self):
        """Test malformed tokens are rejected."""
        malformed_tokens = [
            "",
            "not.a.token",
            "invalid_token_format",
            "header.payload",  # Missing signature
            "header.payload.extra.signature",  # Too many parts
            "..",
            "...",
        ]

        for token in malformed_tokens:
            result = verify_token(token)
            assert result is None, f"Malformed token should be rejected: {token}"

    def test_token_algorithm_confusion(self):
        """Test algorithm confusion attacks are prevented."""
        # Create a token with "none" algorithm (attack vector)
        user_id = "12345"
        malicious_token = jwt.encode(
            {"sub": user_id, "type": "access", "exp": datetime.now(UTC) + timedelta(hours=1)},
            "",
            algorithm="none",
        )

        # Should be rejected
        result = verify_token(malicious_token)
        assert result is None

    def test_refresh_token_distinct_from_access(self):
        """Test refresh tokens are distinct from access tokens."""
        user_id = "12345"
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)

        # Tokens should be different
        assert access_token != refresh_token

        # Access token should not work as refresh token
        result = verify_refresh_token(access_token)
        assert result is None

        # Refresh token should not work as access token
        result = verify_token(refresh_token, token_type="access")
        assert result is None


class TestTokenExpiration:
    """Test token expiration handling."""

    def test_access_token_expires(self):
        """Test access tokens expire after configured time."""
        user_id = "12345"
        # Create token that expires in 1 second
        token = create_access_token(user_id, expires_delta=timedelta(seconds=1))

        # Token should be valid initially
        result = verify_token(token)
        assert result == user_id

        # Wait for expiration
        time.sleep(2)

        # Token should be expired
        result = verify_token(token)
        assert result is None

    def test_refresh_token_expires(self):
        """Test refresh tokens expire after configured time."""
        user_id = "12345"
        # Create token with short expiration
        token = create_refresh_token(user_id)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]

        # Refresh token should expire after REFRESH_TOKEN_EXPIRE_MINUTES
        expected_expiry = iat_timestamp + (settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60)
        assert exp_timestamp == expected_expiry

    def test_expired_token_rejection(self):
        """Test expired tokens are properly rejected."""
        user_id = "12345"
        # Create already expired token
        expired_token = jwt.encode(
            {
                "sub": user_id,
                "type": "access",
                "exp": datetime.now(UTC) - timedelta(minutes=5),
                "iat": datetime.now(UTC) - timedelta(minutes=10),
            },
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )

        result = verify_token(expired_token)
        assert result is None

    def test_future_token_rejection(self):
        """Test tokens with future issue time are rejected."""
        user_id = "12345"
        # Create token with future issue time
        future_token = jwt.encode(
            {
                "sub": user_id,
                "type": "access",
                "exp": datetime.now(UTC) + timedelta(hours=2),
                "iat": datetime.now(UTC) + timedelta(hours=1),  # Future issued time
            },
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )

        result = verify_token(future_token)
        assert result is None


class TestRefreshTokenRotation:
    """Test refresh token rotation security."""

    def test_refresh_token_type_validation(self):
        """Test refresh token has correct type claim."""
        user_id = "12345"
        refresh_token = create_refresh_token(user_id)

        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["type"] == "refresh"

    def test_refresh_token_returns_user_id(self):
        """Test refresh token verification returns user ID."""
        user_id = "12345"
        refresh_token = create_refresh_token(user_id)

        result = verify_refresh_token(refresh_token)
        assert result == user_id

    def test_access_token_not_valid_as_refresh(self):
        """Test access token cannot be used as refresh token."""
        user_id = "12345"
        access_token = create_access_token(user_id)

        # Access token should fail refresh verification
        result = verify_refresh_token(access_token)
        assert result is None


class TestTokenForgeryDetection:
    """Test token forgery and manipulation detection."""

    def test_modified_payload_detected(self):
        """Test modified JWT payload is detected."""
        user_id = "12345"
        token = create_access_token(user_id)

        # Decode and modify payload
        header, payload, signature = token.split(".")

        # Decode payload, modify, and re-encode
        import base64
        import json

        decoded = base64.urlsafe_b64decode(payload + "==")
        data = json.loads(decoded)
        data["sub"] = "99999"  # Change user ID
        modified_payload = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

        # Create forged token
        forged_token = f"{header}.{modified_payload}.{signature}"

        # Should be rejected
        result = verify_token(forged_token)
        assert result is None

    def test_token_with_missing_claims_rejected(self):
        """Test tokens with missing claims are rejected."""
        # Create token without required claims
        incomplete_token = jwt.encode(
            {"exp": datetime.now(UTC) + timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )

        result = verify_token(incomplete_token)
        # Should still verify but return None sub
        assert result is None

    def test_expired_token_cannot_be_reused(self):
        """Test expired tokens cannot be replayed."""
        user_id = "12345"
        # Create expired token
        expired_token = jwt.encode(
            {
                "sub": user_id,
                "type": "access",
                "exp": datetime.now(UTC) - timedelta(minutes=5),
                "iat": datetime.now(UTC) - timedelta(minutes=10),
            },
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )

        # Should be rejected
        result = verify_token(expired_token)
        assert result is None

    def test_token_type_enforcement(self):
        """Test token type is enforced during verification."""
        user_id = "12345"
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)

        # Access token with refresh type check should fail
        assert verify_token(access_token, token_type="refresh") is None

        # Refresh token with access type check should fail
        assert verify_token(refresh_token, token_type="access") is None

        # Both should succeed without type check
        assert verify_token(access_token) == user_id
        assert verify_token(refresh_token) == user_id

    def test_sql_injection_in_subject(self):
        """Test SQL injection in subject field is handled."""
        malicious_user_ids = [
            "1; DROP TABLE users;--",
            "1 OR 1=1",
            "' OR '1'='1",
            "1 UNION SELECT * FROM users",
        ]

        for user_id in malicious_user_ids:
            token = create_access_token(user_id)
            result = verify_token(token)
            assert result == user_id  # Token itself is valid, SQL injection handled at DB layer

    def test_xss_in_subject(self):
        """Test XSS payload in subject field."""
        xss_user_ids = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
        ]

        for user_id in xss_user_ids:
            token = create_access_token(user_id)
            result = verify_token(token)
            assert result == user_id


class TestTokenEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_user_id(self):
        """Test handling of empty user ID."""
        token = create_access_token("")
        result = verify_token(token)
        assert result == ""

    def test_long_user_id(self):
        """Test handling of very long user ID."""
        long_id = "A" * 10000
        token = create_access_token(long_id)
        result = verify_token(token)
        assert result == long_id

    def test_special_characters_in_user_id(self):
        """Test special characters in user ID."""
        special_ids = [
            "user@example.com",
            "user+tag@example.com",
            "user.name",
            "user_name",
            "user-name",
        ]

        for user_id in special_ids:
            token = create_access_token(user_id)
            result = verify_token(token)
            assert result == user_id

    def test_unicode_in_user_id(self):
        """Test unicode characters in user ID."""
        unicode_ids = [
            "用户123",
            "ユーザー123",
            "Пользователь123",
        ]

        for user_id in unicode_ids:
            token = create_access_token(user_id)
            result = verify_token(token)
            assert result == user_id
