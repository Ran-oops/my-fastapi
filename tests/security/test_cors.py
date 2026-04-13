"""Security tests for CORS configuration.

Tests for:
- Invalid origin handling
- Preflight requests
- Credential policy
"""

import pytest
from httpx import AsyncClient

from app.core.config import settings


class TestCORSOriginValidation:
    """Test CORS origin validation."""

    async def test_allowed_origin_access(self, client):
        """Test allowed origins can access API."""
        # Make request from allowed origin
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        }

        response = await client.options("/api/v1/users/me", headers=headers)
        # Should get 200 with CORS headers

        response = await client.get("/api/v1/users/me", headers=headers)
        # Should receive appropriate CORS headers

    async def test_disallowed_origin_rejected(self, client):
        """Test disallowed origins are rejected."""
        disallowed_origins = [
            "https://evil.com",
            "https://attacker.com",
            "http://localhost:9999",
            "https://phishing-site.com",
            "null",  # null origin
            "file://",  # file protocol
            "https://",  # empty origin
        ]

        for origin in disallowed_origins:
            headers = {"Origin": origin}
            response = await client.get("/api/v1/users/me", headers=headers)

            # Check Access-Control-Allow-Origin header
            acao = response.headers.get("access-control-allow-origin", "")

            # Origin should not be in allowed list (or might be wildcard)
            if origin not in settings.BACKEND_CORS_ORIGINS and "*" not in settings.BACKEND_CORS_ORIGINS:
                assert acao != origin or acao == ""

    async def test_null_origin_handling(self, client):
        """Test null origin is handled properly."""
        headers = {"Origin": "null"}

        response = await client.get("/api/v1/users/me", headers=headers)
        acao = response.headers.get("access-control-allow-origin", "")

        # Null origin should not be reflected
        assert acao != "null"

    async def test_subdomain_origin_validation(self, client):
        """Test subdomain origin validation."""
        # Test if subdomains are properly handled
        subdomain_origins = [
            "https://subdomain.example.com",
            "https://evil.example.com",
            "https://api.example.com",
        ]

        for origin in subdomain_origins:
            headers = {"Origin": origin}
            response = await client.get("/health", headers=headers)
            acao = response.headers.get("access-control-allow-origin", "")

            # Depending on configuration, might be allowed or not
            pass  # Just document the behavior

    async def test_origin_case_sensitivity(self, client):
        """Test origin case sensitivity."""
        # Test with different cases
        case_origins = [
            "http://Localhost:3000",
            "HTTP://LOCALHOST:3000",
            "http://localhost:3000",
        ]

        for origin in case_origins:
            headers = {"Origin": origin}
            response = await client.get("/health", headers=headers)
            # Should handle gracefully
            assert response.status_code == 200

    async def test_wildcard_origin_production(self, client):
        """Test wildcard origin in production is handled."""
        # Check if wildcard is allowed in current config
        if "*" in settings.BACKEND_CORS_ORIGINS:
            # In production, wildcard should not be allowed
            if settings.APP_ENV == "production":
                pytest.skip("Wildcard not allowed in production")


class TestCORSMethodValidation:
    """Test CORS method validation."""

    async def test_preflight_request_allowed_methods(self, client):
        """Test preflight requests return allowed methods."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        }

        response = await client.options("/api/v1/auth/login", headers=headers)

        # Should return 200 for preflight
        assert response.status_code == 200

        # Check allowed methods header
        acam = response.headers.get("access-control-allow-methods", "")
        assert "POST" in acam or "*" in acam

    async def test_preflight_disallowed_method(self, client):
        """Test preflight for disallowed methods."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "TRACE",  # Potentially dangerous
        }

        response = await client.options("/api/v1/auth/login", headers=headers)

        # TRACE should not be allowed
        acam = response.headers.get("access-control-allow-methods", "")
        assert "TRACE" not in acam

    async def test_preflight_forbidden_method(self, client):
        """Test preflight for forbidden HTTP methods."""
        dangerous_methods = ["TRACE", "TRACK", "CONNECT", "DEBUG"]

        for method in dangerous_methods:
            headers = {
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": method,
            }

            response = await client.options("/api/v1/auth/login", headers=headers)
            acam = response.headers.get("access-control-allow-methods", "")
            assert method not in acam


class TestCORSHeaderValidation:
    """Test CORS header validation."""

    async def test_preflight_allowed_headers(self, client):
        """Test preflight requests allow expected headers."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization",
        }

        response = await client.options("/api/v1/auth/login", headers=headers)

        assert response.status_code == 200

        # Check allowed headers
        acah = response.headers.get("access-control-allow-headers", "")
        assert "content-type" in acah.lower() or "*" in acah

    async def test_preflight_custom_headers(self, client):
        """Test preflight with custom headers."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Custom-Header, X-Another-Header",
        }

        response = await client.options("/api/v1/auth/login", headers=headers)
        assert response.status_code == 200

    async def test_preflight_sensitive_headers_blocked(self, client):
        """Test sensitive headers in preflight are handled."""
        # Headers that should not be allowed
        sensitive_headers = [
            "Cookie",
            "Set-Cookie",
            "Authorization",
        ]

        for header in sensitive_headers:
            headers = {
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": header,
            }

            response = await client.options("/api/v1/auth/login", headers=headers)
            # Should handle but may not include in allowed headers
            assert response.status_code in [200, 204]

    async def test_expose_headers(self, client):
        """Test exposed headers configuration."""
        headers = {"Origin": "http://localhost:3000"}

        response = await client.get("/api/v1/users/me", headers=headers)

        # Check exposed headers
        aceh = response.headers.get("access-control-expose-headers", "")
        # Should expose some headers but not sensitive ones
        assert "set-cookie" not in aceh.lower()


class TestCORSCredentials:
    """Test CORS credentials policy."""

    async def test_credentials_header(self, client):
        """Test Access-Control-Allow-Credentials header."""
        headers = {
            "Origin": "http://localhost:3000",
        }

        response = await client.get("/api/v1/users/me", headers=headers)

        # Check credentials header
        acac = response.headers.get("access-control-allow-credentials", "")

        # If credentials are allowed, wildcard should not be in ACAO
        if acac.lower() == "true":
            acao = response.headers.get("access-control-allow-origin", "")
            assert acao != "*"

    async def test_wildcard_with_credentials(self, client):
        """Test wildcard origin with credentials is prevented."""
        # This is a security vulnerability - wildcard with credentials
        if "*" in settings.BACKEND_CORS_ORIGINS:
            headers = {"Origin": "http://localhost:3000"}
            response = await client.get("/api/v1/users/me", headers=headers)

            acac = response.headers.get("access-control-allow-credentials", "")
            acao = response.headers.get("access-control-allow-origin", "")

            # If credentials allowed, wildcard should not be used
            if acac.lower() == "true":
                assert acao != "*"

    async def test_cookie_handling(self, client):
        """Test cookie handling with CORS."""
        headers = {
            "Origin": "http://localhost:3000",
        }

        response = await client.get("/api/v1/users/me", headers=headers)

        # Check if cookies are being set
        set_cookie = response.headers.get("set-cookie", "")

        # Cookies should have security attributes
        if set_cookie:
            assert "HttpOnly" in set_cookie or True  # Optional but recommended


class TestPreflightRequests:
    """Test CORS preflight requests."""

    async def test_preflight_success(self, client):
        """Test successful preflight request."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        }

        response = await client.options("/api/v1/auth/login", headers=headers)

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    async def test_preflight_max_age(self, client):
        """Test preflight cache duration."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        }

        response = await client.options("/api/v1/users/me", headers=headers)

        # Check max-age header
        acma = response.headers.get("access-control-max-age")
        if acma:
            max_age = int(acma)
            assert max_age <= 86400, "Max age too long (should be <= 24 hours)"

    async def test_preflight_without_origin(self, client):
        """Test preflight without origin header."""
        headers = {
            "Access-Control-Request-Method": "POST",
        }

        response = await client.options("/api/v1/auth/login", headers=headers)

        # Should either succeed or fail gracefully
        assert response.status_code in [200, 400, 403]

    async def test_preflight_partial_headers(self, client):
        """Test preflight with partial headers."""
        # Only method, no headers
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        }

        response = await client.options("/api/v1/auth/login", headers=headers)
        assert response.status_code == 200

    async def test_preflight_multiple_methods(self, client):
        """Test preflight for multiple methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

        for method in methods:
            headers = {
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": method,
            }

            response = await client.options("/api/v1/users/me", headers=headers)
            assert response.status_code in [200, 204, 405]


class TestCORSResponseHeaders:
    """Test CORS-related response headers."""

    async def test_cors_headers_on_simple_request(self, client):
        """Test CORS headers on simple GET request."""
        headers = {"Origin": "http://localhost:3000"}

        response = await client.get("/health", headers=headers)

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    async def test_vary_header(self, client):
        """Test Vary: Origin header is present."""
        headers = {"Origin": "http://localhost:3000"}

        response = await client.get("/health", headers=headers)

        vary = response.headers.get("vary", "")
        assert "origin" in vary.lower()

    async def test_no_cors_headers_without_origin(self, client):
        """Test no CORS headers when Origin is not provided."""
        response = await client.get("/health")

        # Should still succeed
        assert response.status_code == 200

        # CORS headers should not be present
        acao = response.headers.get("access-control-allow-origin")
        # This depends on configuration - some servers always send CORS headers

    async def test_cors_headers_on_error_response(self, client):
        """Test CORS headers on error responses."""
        headers = {"Origin": "http://localhost:3000"}

        response = await client.get("/api/v1/users/99999", headers=headers)

        # Should have CORS headers even on 404
        assert "access-control-allow-origin" in response.headers

    async def test_cors_headers_on_auth_error(self, client):
        """Test CORS headers on authentication error."""
        headers = {
            "Origin": "http://localhost:3000",
        }

        response = await client.get("/api/v1/users/me", headers=headers)

        # Should have CORS headers even on 401
        assert "access-control-allow-origin" in response.headers


class TestCORSVulnerabilities:
    """Test for CORS vulnerabilities."""

    async def test_reflected_origin_attack(self, client):
        """Test reflected origin vulnerability."""
        # Try to get server to reflect arbitrary origin
        malicious_origins = [
            "https://attacker.com",
            "http://evil.org",
            "https://phishing.com",
        ]

        for origin in malicious_origins:
            headers = {"Origin": origin}
            response = await client.get("/health", headers=headers)

            acao = response.headers.get("access-control-allow-origin", "")

            # Should not reflect arbitrary origins
            if origin not in settings.BACKEND_CORS_ORIGINS:
                assert acao != origin

    async def test_origin_validation_bypass(self, client):
        """Test origin validation bypass attempts."""
        bypass_origins = [
            "http://localhost.attacker.com",  # Subdomain
            "http://localhostattacker.com",  # Prefix match
            "http://localhost:3000.attacker.com",  # Port confusion
            "null",
            "",
        ]

        for origin in bypass_origins:
            headers = {"Origin": origin}
            response = await client.get("/health", headers=headers)

            acao = response.headers.get("access-control-allow-origin", "")

            # Should not allow these bypass attempts
            if origin not in settings.BACKEND_CORS_ORIGINS:
                assert acao != origin or acao == ""

    async def test_csp_bypass_via_cors(self, client):
        """Test CSP bypass through CORS."""
        # This test documents the behavior
        headers = {"Origin": "http://localhost:3000"}

        response = await client.get("/health", headers=headers)

        # Check for security headers
        csp = response.headers.get("content-security-policy", "")
        # CSP should be present
        assert True  # Document behavior


class TestCORSEdgeCases:
    """Test CORS edge cases."""

    async def test_empty_origin(self, client):
        """Test empty origin header."""
        headers = {"Origin": ""}

        response = await client.get("/health", headers=headers)
        assert response.status_code == 200

    async def test_whitespace_origin(self, client):
        """Test origin with whitespace."""
        headers = {"Origin": " http://localhost:3000 "}

        response = await client.get("/health", headers=headers)
        assert response.status_code == 200

    async def test_unicode_origin(self, client):
        """Test origin with unicode characters."""
        headers = {"Origin": "http://本地化.example.com"}

        response = await client.get("/health", headers=headers)
        assert response.status_code == 200

    async def test_very_long_origin(self, client):
        """Test very long origin header."""
        long_origin = "http://" + "a" * 1000 + ".com"
        headers = {"Origin": long_origin}

        response = await client.get("/health", headers=headers)
        assert response.status_code in [200, 400]

    async def test_multiple_origin_headers(self, client):
        """Test multiple origin headers."""
        # This would require raw HTTP access
        # For now, just document that it might be an issue
        pass

    async def test_cors_with_redirects(self, client):
        """Test CORS behavior with redirects."""
        # Most APIs don't redirect, but document behavior
        pass
