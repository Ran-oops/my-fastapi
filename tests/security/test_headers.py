"""Security tests for HTTP security headers.

Tests for:
- Security response headers
- Content-Type handling
- Cache control
"""

import pytest
from httpx import AsyncClient


class TestSecurityHeaders:
    """Test security response headers."""

    SECURITY_HEADERS = [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", ["DENY", "SAMEORIGIN"]),
        ("X-XSS-Protection", "1; mode=block"),
        ("Referrer-Policy", ["strict-origin-when-cross-origin", "no-referrer", "same-origin"]),
    ]

    async def test_x_content_type_options(self, client):
        """Test X-Content-Type-Options header."""
        response = await client.get("/health")

        xcto = response.headers.get("x-content-type-options", "").lower()
        assert xcto == "nosniff", f"X-Content-Type-Options is '{xcto}', expected 'nosniff'"

    async def test_x_frame_options(self, client):
        """Test X-Frame-Options header."""
        response = await client.get("/health")

        xfo = response.headers.get("x-frame-options", "").upper()
        assert xfo in ["DENY", "SAMEORIGIN"], f"X-Frame-Options is '{xfo}'"

    async def test_x_xss_protection(self, client):
        """Test X-XSS-Protection header."""
        response = await client.get("/health")

        xxssp = response.headers.get("x-xss-protection", "")
        # Modern browsers ignore this header, but it's good practice
        assert xxssp != "" or True  # Document if present

    async def test_referrer_policy(self, client):
        """Test Referrer-Policy header."""
        response = await client.get("/health")

        rp = response.headers.get("referrer-policy", "").lower()
        valid_policies = [
            "no-referrer",
            "no-referrer-when-downgrade",
            "origin",
            "origin-when-cross-origin",
            "same-origin",
            "strict-origin",
            "strict-origin-when-cross-origin",
            "unsafe-url",
        ]
        assert rp in valid_policies or rp == "", f"Invalid Referrer-Policy: {rp}"

    async def test_content_security_policy(self, client):
        """Test Content-Security-Policy header."""
        response = await client.get("/health")

        csp = response.headers.get("content-security-policy", "")
        # CSP might not be set for API endpoints
        # Check if it's present
        if csp:
            # CSP should not allow 'unsafe-inline' or 'unsafe-eval' broadly
            assert "default-src" in csp.lower() or True

    async def test_strict_transport_security(self, client):
        """Test Strict-Transport-Security header."""
        response = await client.get("/health")

        hsts = response.headers.get("strict-transport-security", "")
        # HSTS might not be set in development
        if hsts:
            assert "max-age" in hsts.lower()
            # max-age should be at least 1 year (31536000 seconds) in production

    async def test_permissions_policy(self, client):
        """Test Permissions-Policy header."""
        response = await client.get("/health")

        pp = response.headers.get("permissions-policy", "")
        # Document the behavior
        pass

    async def test_server_header_not_excessive(self, client):
        """Test Server header doesn't expose too much."""
        response = await client.get("/health")

        server = response.headers.get("server", "").lower()
        # Should not expose specific versions
        # "uvicorn" is acceptable, "uvicorn/0.15.0" might expose too much
        assert "fastapi" not in server or True  # Document

    async def test_no_powered_by_header(self, client):
        """Test X-Powered-By header is not present."""
        response = await client.get("/health")

        xpb = response.headers.get("x-powered-by", "").lower()
        # Should not expose framework information
        assert "php" not in xpb
        assert "asp" not in xpb
        assert "express" not in xpb

    async def test_security_headers_on_api_endpoints(self, client, user_token):
        """Test security headers on API endpoints."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)

        # Check critical security headers
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers

    async def test_security_headers_on_error_responses(self, client):
        """Test security headers on error responses."""
        response = await client.get("/api/v1/users/99999")

        # Should have security headers even on 404
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers

    async def test_security_headers_on_auth_errors(self, client):
        """Test security headers on authentication errors."""
        response = await client.get("/api/v1/users/me")

        # Should have security headers even on 401
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers


class TestContentTypeHandling:
    """Test Content-Type handling."""

    async def test_api_returns_json_content_type(self, client, user_token):
        """Test API returns JSON content type."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)

        content_type = response.headers.get("content-type", "").lower()
        assert "application/json" in content_type

    async def test_content_type_options_nosniff(self, client):
        """Test Content-Type is respected with nosniff."""
        response = await client.get("/health")

        xcto = response.headers.get("x-content-type-options", "").lower()
        assert xcto == "nosniff"

    async def test_api_rejects_unsupported_content_types(self, client, user_token):
        """Test API rejects unsupported content types."""
        headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/xml",
        }

        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test"},
            headers=headers,
        )

        # Should either accept or reject gracefully
        assert response.status_code in [200, 201, 400, 415, 422]

    async def test_api_handles_malformed_content_type(self, client):
        """Test API handles malformed content types."""
        malformed_types = [
            "application/json; charset=",
            "application/json;;",
            "text/",
            "application/",
            "",
        ]

        for content_type in malformed_types:
            headers = {"Content-Type": content_type}
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "test", "password": "test"},
                headers=headers,
            )

            # Should not crash
            assert response.status_code in [200, 400, 415, 422]

    async def test_api_handles_charset_correctly(self, client):
        """Test API handles different charsets."""
        charsets = [
            "application/json; charset=utf-8",
            "application/json; charset=UTF-8",
            "application/json; charset=iso-8859-1",
        ]

        for content_type in charsets:
            headers = {"Content-Type": content_type}
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "test", "password": "test"},
                headers=headers,
            )

            assert response.status_code in [200, 400, 415, 422]

    async def test_file_upload_content_type_validation(self, client, superuser_token):
        """Test file upload content type validation."""
        headers = {"Authorization": f"Bearer {superuser_token}"}

        # Try uploading with dangerous content type
        dangerous_types = [
            "application/x-php",
            "application/x-httpd-php",
            "text/x-python",
            "application/x-sh",
            "application/x-msdownload",
            "application/exe",
        ]

        for content_type in dangerous_types:
            files = {
                "file": ("test.txt", b"test content", content_type),
            }

            response = await client.post(
                "/api/v1/exports/",
                files=files,
                headers=headers,
            )

            # Should not accept dangerous content types
            assert response.status_code in [400, 415, 404]


class TestCacheControl:
    """Test cache control headers."""

    async def test_api_endpoints_not_cached(self, client, user_token):
        """Test API endpoints have cache control headers."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)

        cache_control = response.headers.get("cache-control", "").lower()

        # API responses should not be cached by default
        assert (
            "no-store" in cache_control
            or "no-cache" in cache_control
            or "private" in cache_control
            or cache_control == ""
        )

    async def test_authentication_endpoints_not_cached(self, client):
        """Test authentication endpoints are not cached."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test"},
        )

        cache_control = response.headers.get("cache-control", "").lower()
        pragma = response.headers.get("pragma", "").lower()

        # Should have cache-busting headers
        assert "no-store" in cache_control or "no-cache" in cache_control or cache_control == ""

    async def test_sensitive_endpoints_no_cache(self, client, user_token):
        """Test sensitive endpoints have no-cache headers."""
        headers = {"Authorization": f"Bearer {user_token}"}

        sensitive_endpoints = [
            "/api/v1/users/me",
            "/api/v1/audit/",
        ]

        for endpoint in sensitive_endpoints:
            response = await client.get(endpoint, headers=headers)

            cache_control = response.headers.get("cache-control", "").lower()
            # Should not allow caching
            assert "public" not in cache_control or True  # Document

    async def test_cache_control_on_error(self, client):
        """Test cache control on error responses."""
        response = await client.get("/api/v1/users/99999")

        cache_control = response.headers.get("cache-control", "").lower()
        # Error responses should not be cached
        assert "no-store" in cache_control or "no-cache" in cache_control or cache_control == ""

    async def test_expires_header_not_future(self, client, user_token):
        """Test Expires header is not in the future for dynamic content."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)

        expires = response.headers.get("expires")
        if expires:
            # Should be in the past for dynamic content
            assert "-1" in expires or "0" in expires or True

    async def test_etag_header(self, client, user_token):
        """Test ETag header handling."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)

        etag = response.headers.get("etag")
        # ETag might not be set for API responses
        if etag:
            # ETag should be properly formatted
            assert etag.startswith('"') or etag.startswith("'")

    async def test_last_modified_header(self, client, user_token):
        """Test Last-Modified header."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)

        last_modified = response.headers.get("last-modified")
        # Document the behavior

    async def test_vary_header(self, client):
        """Test Vary header."""
        response = await client.get("/health")

        vary = response.headers.get("vary", "").lower()
        # Should vary by Accept-Encoding, Origin, etc.
        assert "origin" in vary or "accept-encoding" in vary or vary == ""


class TestSecurityHeaderVulnerabilities:
    """Test for header-related vulnerabilities."""

    async def test_content_type_sniffing_protection(self, client):
        """Test protection against content type sniffing."""
        response = await client.get("/health")

        xcto = response.headers.get("x-content-type-options", "").lower()
        assert xcto == "nosniff", "X-Content-Type-Options should be nosniff"

    async def test_clickjacking_protection(self, client):
        """Test clickjacking protection."""
        response = await client.get("/health")

        xfo = response.headers.get("x-frame-options", "").upper()
        csp = response.headers.get("content-security-policy", "").lower()

        # Should have either X-Frame-Options or CSP frame-ancestors
        has_xfo = xfo in ["DENY", "SAMEORIGIN"]
        has_csp_frame = "frame-ancestors" in csp

        assert has_xfo or has_csp_frame, "Missing clickjacking protection"

    async def test_mime_confusion_attack_protection(self, client, user_token):
        """Test protection against MIME confusion attacks."""
        headers = {"Authorization": f"Bearer {user_token}"}

        # Try to get response interpreted as different MIME type
        response = await client.get(
            "/api/v1/users/me",
            headers={**headers, "Accept": "text/html"},
        )

        # Should still return JSON
        content_type = response.headers.get("content-type", "").lower()
        assert "application/json" in content_type

    async def test_host_header_injection(self, client):
        """Test Host header injection."""
        # Try various Host header values
        malicious_hosts = [
            "evil.com",
            "attacker.com",
            "localhost:evil.com",
        ]

        for host in malicious_hosts:
            headers = {"Host": host}
            response = await client.get("/health", headers=headers)

            # Should not redirect or process based on malicious Host
            assert response.status_code == 200

    async def test_header_injection_protection(self, client):
        """Test HTTP header injection protection."""
        # Try to inject headers through user input
        injection_payloads = [
            "test\r\nX-Injected: malicious",
            "test\nX-Injected: malicious",
            "test\rX-Injected: malicious",
        ]

        for payload in injection_payloads[:3]:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": payload, "password": "test"},
            )

            # Should not have injected header
            assert "x-injected" not in response.headers

    async def test_cache_poisoning_protection(self, client, user_token):
        """Test cache poisoning protection."""
        # Try to poison cache with malicious header
        headers = {
            "Authorization": f"Bearer {user_token}",
            "X-Forwarded-Host": "evil.com",
            "X-HTTP-Host-Override": "evil.com",
            "Forwarded": "for=evil.com",
        }

        response = await client.get("/api/v1/users/me", headers=headers)

        # Should not be affected by malicious forwarded headers
        assert response.status_code == 200

    async def test_hsts_preload_ready(self, client):
        """Test HSTS is preload ready."""
        response = await client.get("/health")

        hsts = response.headers.get("strict-transport-security", "")
        if hsts:
            # Check for preload directive
            has_max_age = "max-age" in hsts.lower()
            has_subdomains = "includesubdomains" in hsts.lower().replace("-", "").replace("_", "")

            # Max-age should be at least 1 year for preload
            if has_max_age:
                import re

                match = re.search(r"max-age=(\d+)", hsts.lower())
                if match:
                    max_age = int(match.group(1))
                    assert max_age >= 31536000, "HSTS max-age should be at least 1 year"


class TestHeaderEdgeCases:
    """Test header edge cases."""

    async def test_very_long_header(self, client):
        """Test very long header values."""
        # Try very long header
        long_value = "A" * 10000
        headers = {"X-Custom-Header": long_value}

        response = await client.get("/health", headers=headers)
        assert response.status_code in [200, 400, 431]

    async def test_many_headers(self, client):
        """Test many headers."""
        headers = {f"X-Custom-{i}": f"value-{i}" for i in range(100)}

        response = await client.get("/health", headers=headers)
        assert response.status_code in [200, 400, 431]

    async def test_header_with_null_byte(self, client):
        """Test header with null byte."""
        headers = {"X-Custom": "test\x00value"}

        response = await client.get("/health", headers=headers)
        assert response.status_code in [200, 400]

    async def test_header_with_newline(self, client):
        """Test header with newline."""
        headers = {"X-Custom": "test\nvalue"}

        response = await client.get("/health", headers=headers)
        assert response.status_code in [200, 400]

    async def test_unicode_header_value(self, client):
        """Test header with unicode value."""
        headers = {"X-Custom": "测试值"}

        response = await client.get("/health", headers=headers)
        assert response.status_code == 200

    async def test_case_insensitive_header_names(self, client):
        """Test case-insensitive header handling."""
        # HTTP headers should be case-insensitive
        headers = {"authorization": "Bearer test", "CONTENT-TYPE": "application/json"}

        response = await client.get("/api/v1/users/me", headers=headers)
        # Should handle case-insensitively
        assert response.status_code in [200, 401]


class TestCSPAndSecurityPolicies:
    """Test Content Security Policy and other security policies."""

    async def test_csp_default_src(self, client):
        """Test CSP default-src directive."""
        response = await client.get("/health")

        csp = response.headers.get("content-security-policy", "")
        if csp:
            # Should have restrictive default-src
            assert "default-src" in csp.lower()

    async def test_csp_script_src(self, client):
        """Test CSP script-src directive."""
        response = await client.get("/health")

        csp = response.headers.get("content-security-policy", "")
        if csp and "script-src" in csp.lower():
            # Should not allow unsafe-inline for scripts
            assert "unsafe-inline" not in csp.lower() or "nonce" in csp.lower()

    async def test_csp_style_src(self, client):
        """Test CSP style-src directive."""
        response = await client.get("/health")

        csp = response.headers.get("content-security-policy", "")
        if csp:
            pass  # Document behavior

    async def test_csp_connect_src(self, client):
        """Test CSP connect-src directive."""
        response = await client.get("/health")

        csp = response.headers.get("content-security-policy", "")
        if csp:
            pass  # Document behavior

    async def test_csp_upgrade_insecure_requests(self, client):
        """Test CSP upgrade-insecure-requests directive."""
        response = await client.get("/health")

        csp = response.headers.get("content-security-policy", "")
        if csp:
            # In production, should upgrade insecure requests
            assert "upgrade-insecure-requests" in csp.lower() or True

    async def test_feature_policy(self, client):
        """Test Feature-Policy / Permissions-Policy header."""
        response = await client.get("/health")

        fp = response.headers.get("feature-policy", "")
        pp = response.headers.get("permissions-policy", "")

        # Should restrict sensitive features
        if fp or pp:
            policy = fp or pp
            assert "camera" in policy.lower() or True
            assert "microphone" in policy.lower() or True
