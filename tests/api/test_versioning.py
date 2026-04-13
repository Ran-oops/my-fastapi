"""Tests for API versioning functionality."""

import pytest
from httpx import AsyncClient

from app.api.versioning import LATEST_VERSION, VERSIONS, is_deprecated
from app.main import app


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestVersionInfo:
    """Test version metadata."""

    def test_version_info_structure(self):
        """Test version info has correct structure."""
        for version, info in VERSIONS.items():
            assert info.major == version
            assert info.minor >= 0
            assert info.patch >= 0
            assert info.status in [
                "development",
                "beta",
                "current",
                "deprecated",
                "sunset",
            ]
            assert info.description

    def test_latest_version(self):
        """Test latest version is valid."""
        assert LATEST_VERSION in VERSIONS
        info = VERSIONS[LATEST_VERSION]
        assert info.status in ["current", "beta"]

    def test_deprecated_detection(self):
        """Test deprecated version detection."""
        # v1 should be deprecated
        assert is_deprecated(1) is True
        # v2 should not be deprecated
        assert is_deprecated(2) is False


class TestVersionEndpoints:
    """Test version-related endpoints."""

    @pytest.mark.asyncio
    async def test_versions_endpoint(self, client):
        """Test /versions endpoint."""
        response = await client.get("/versions")
        assert response.status_code == 200
        data = response.json()

        assert "versions" in data
        assert "latest" in data
        assert "current" in data
        assert "deprecated" in data

    @pytest.mark.asyncio
    async def test_version_detail_endpoint(self, client):
        """Test /versions/{version} endpoint."""
        response = await client.get("/versions/2")
        assert response.status_code == 200
        data = response.json()

        assert data["version"] == "2.0.0"
        assert data["status"] == "current"
        assert "endpoints" in data
        assert data["endpoints"]["base"] == "/api/v2"

    @pytest.mark.asyncio
    async def test_version_detail_not_found(self, client):
        """Test /versions/{version} with invalid version."""
        response = await client.get("/versions/999")
        assert response.status_code == 404
        assert "error" in response.json()


class TestVersionedRoutes:
    """Test versioned API routes."""

    @pytest.mark.asyncio
    async def test_v1_users_endpoint(self, client):
        """Test v1 users endpoint exists."""
        response = await client.get("/api/v1/users")
        # Should return 401 (unauthorized) or 403, not 404
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_v2_users_endpoint(self, client):
        """Test v2 users endpoint exists."""
        response = await client.get("/api/v2/users")
        # Should return 401 (unauthorized) or 403, not 404
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root endpoint returns version info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()

        assert "versions" in data
        assert "v1" in data["versions"]
        assert "v2" in data["versions"]


class TestDeprecationHeaders:
    """Test deprecation headers."""

    @pytest.mark.asyncio
    async def test_v1_returns_deprecation_headers(self, client):
        """Test v1 returns deprecation headers."""
        response = await client.get("/api/v1/users")

        # Check for deprecation headers
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "1"
        assert "X-API-Latest-Version" in response.headers

    @pytest.mark.asyncio
    async def test_v2_no_deprecation_headers(self, client):
        """Test v2 does not return deprecation headers."""
        response = await client.get("/api/v2/users")

        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "2"
        assert "X-API-Latest-Version" in response.headers


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Test basic health check."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "api_version" in data
        assert "api_latest" in data

    @pytest.mark.asyncio
    async def test_health_ready_endpoint(self, client):
        """Test readiness probe."""
        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "databases" in data

    @pytest.mark.asyncio
    async def test_health_version_endpoint(self, client):
        """Test version health check."""
        response = await client.get("/health/version-info")
        assert response.status_code == 200
        data = response.json()

        assert "versions" in data
        assert "total" in data["versions"]
        assert "current" in data["versions"]
        assert "deprecated" in data["versions"]


class TestLatestAlias:
    """Test /api/latest alias."""

    @pytest.mark.asyncio
    async def test_latest_alias_exists(self, client):
        """Test /api/latest endpoint exists."""
        response = await client.get("/api/latest/")
        # Should be handled by the alias
        assert response.status_code in [200, 307, 308]
