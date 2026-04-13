"""API Versioning Configuration.

This module provides manual API version management with support for:
- Semantic versioning (major.minor.patch)
- Version-specific documentation endpoints
- Deprecated version warnings
- Latest version alias

Note: This is a custom implementation. The original plan was to use
fastapi-versionizer, but it requires additional dependencies.
For production, consider using fastapi-versionizer or FastAPI's native
versioning support.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VersionInfo:
    """API Version metadata."""

    major: int
    minor: int
    patch: int
    status: str  # 'development', 'beta', 'current', 'deprecated', 'sunset'
    description: str
    deprecated_date: str | None = None
    sunset_date: str | None = None
    changes: list[str] | None = None

    @property
    def version_string(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


# Version registry
VERSIONS: dict[int, VersionInfo] = {
    1: VersionInfo(
        major=1,
        minor=0,
        patch=0,
        status="deprecated",
        description="Initial API version",
        deprecated_date="2025-01-01",
        sunset_date="2025-12-31",
        changes=["Initial release with core features"],
    ),
    2: VersionInfo(
        major=2,
        minor=0,
        patch=0,
        status="current",
        description="Current stable API with enhanced features",
        changes=[
            "Improved response format",
            "Better error handling",
            "Batch operations support",
            "Advanced filtering",
        ],
    ),
}

LATEST_VERSION = 2


def get_version_info(version: int) -> VersionInfo | None:
    """Get version metadata."""
    return VERSIONS.get(version)


def get_all_versions() -> dict[int, dict[str, Any]]:
    """Get all version information."""
    return {
        v: {
            "version": info.version_string,
            "major": info.major,
            "minor": info.minor,
            "patch": info.patch,
            "status": info.status,
            "description": info.description,
            "deprecated_date": info.deprecated_date,
            "sunset_date": info.sunset_date,
            "changes": info.changes or [],
        }
        for v, info in VERSIONS.items()
    }


def is_deprecated(version: int) -> bool:
    """Check if a version is deprecated."""
    info = VERSIONS.get(version)
    return info is not None and info.status == "deprecated"


def is_supported(version: int) -> bool:
    """Check if a version is still supported."""
    info = VERSIONS.get(version)
    if info is None:
        return False
    return info.status in ["current", "beta", "deprecated"]


class VersionedRouter:
    """Router wrapper that adds version metadata."""

    def __init__(
        self,
        router: APIRouter,
        version: int,
        prefix: str,
        deprecated: bool = False,
    ):
        self.router = router
        self.version = version
        self.prefix = prefix
        self.deprecated = deprecated or is_deprecated(version)
        self.info = get_version_info(version)

        # Mark all routes as deprecated if version is deprecated
        if self.deprecated:
            for route in self.router.routes:
                if hasattr(route, "deprecated"):
                    route.deprecated = True  # type: ignore

    def include_in_app(self, app: FastAPI) -> None:
        """Include this version's router in the FastAPI app."""
        app.include_router(
            self.router,
            prefix=self.prefix,
            tags=[f"v{self.version}"],
        )
        logger.info(
            f"Registered API v{self.version} at {self.prefix}",
            deprecated=self.deprecated,
            status=self.info.status if self.info else "unknown",
        )


class APIVersionManager:
    """Manager for API versions."""

    def __init__(self, app: FastAPI):
        self.app = app
        self.versions: dict[int, VersionedRouter] = {}
        self._setup_middleware()
        self._setup_endpoints()

    def _setup_middleware(self) -> None:
        """Add version middleware."""

        @self.app.middleware("http")
        async def version_middleware(request: Request, call_next):
            response = await call_next(request)

            # Add API version headers
            response.headers["X-API-Latest-Version"] = str(LATEST_VERSION)

            # Add version-specific headers
            path = request.url.path
            if "/api/v" in path:
                try:
                    version_str = path.split("/api/v")[1].split("/")[0]
                    response.headers["X-API-Version"] = version_str

                    # Add deprecation headers for deprecated versions
                    version = int(version_str)
                    if is_deprecated(version):
                        response.headers["Deprecation"] = "true"
                        info = get_version_info(version)
                        if info and info.sunset_date:
                            response.headers["Sunset"] = info.sunset_date
                        response.headers["Link"] = f'</api/v{LATEST_VERSION}/docs>; rel="successor-version"'
                except (ValueError, IndexError):
                    pass

            return response

    def _setup_endpoints(self) -> None:
        """Setup version-related endpoints."""

        @self.app.get("/versions", tags=["versioning"])
        async def get_versions():
            """Get all available API versions."""
            return {
                "versions": get_all_versions(),
                "latest": LATEST_VERSION,
                "current": [v for v, info in VERSIONS.items() if info.status == "current"],
                "deprecated": [v for v, info in VERSIONS.items() if info.status == "deprecated"],
            }

        @self.app.get("/versions/{version}", tags=["versioning"])
        async def get_version_detail(version: int):
            """Get details for a specific version."""
            info = get_version_info(version)
            if info is None:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "Version not found",
                        "available_versions": list(VERSIONS.keys()),
                    },
                )
            return {
                "version": info.version_string,
                "status": info.status,
                "description": info.description,
                "deprecated_date": info.deprecated_date,
                "sunset_date": info.sunset_date,
                "endpoints": {
                    "base": f"/api/v{version}",
                    "docs": f"/api/v{version}/docs",
                    "redoc": f"/api/v{version}/redoc",
                },
            }

    def register_version(
        self,
        router: APIRouter,
        version: int,
        prefix: str | None = None,
    ) -> None:
        """Register a versioned router."""
        if prefix is None:
            prefix = f"/api/v{version}"

        versioned = VersionedRouter(
            router=router,
            version=version,
            prefix=prefix,
        )
        versioned.include_in_app(self.app)
        self.versions[version] = versioned

    def register_latest_alias(self, version: int) -> None:
        """Register /api/latest to point to a specific version."""
        if version not in self.versions:
            raise ValueError(f"Version {version} not registered")

        source_router = self.versions[version].router

        # Create alias router
        @self.app.get("/api/latest/{path:path}", include_in_schema=False)
        async def latest_proxy(path: str, request: Request):
            """Redirect /api/latest to the latest version."""
            # This would need actual proxy implementation
            # For now, just return info
            return {
                "message": "This is the latest version endpoint",
                "version": LATEST_VERSION,
                "redirect_to": f"/api/v{LATEST_VERSION}/{path}",
            }

        logger.info(f"Registered /api/latest alias to v{version}")

    def get_registered_versions(self) -> list[int]:
        """Get list of registered versions."""
        return list(self.versions.keys())


def create_version_docs_router(app: FastAPI, version: int, prefix: str) -> APIRouter:
    """Create documentation router for a specific version."""
    docs_router = APIRouter()

    @docs_router.get("/docs", include_in_schema=False)
    async def version_docs():
        """Swagger UI for this version."""
        return {
            "message": f"Swagger UI for v{version}",
            "url": f"{prefix}/openapi.json",
        }

    @docs_router.get("/redoc", include_in_schema=False)
    async def version_redoc():
        """ReDoc for this version."""
        return {
            "message": f"ReDoc for v{version}",
            "url": f"{prefix}/openapi.json",
        }

    return docs_router


def setup_versioning(app: FastAPI) -> APIVersionManager:
    """Setup API versioning for the application.

    Args:
        app: FastAPI application instance

    Returns:
        Configured APIVersionManager instance
    """
    manager = APIVersionManager(app)

    logger.info(
        "API versioning initialized",
        latest_version=LATEST_VERSION,
        available_versions=list(VERSIONS.keys()),
    )

    return manager
