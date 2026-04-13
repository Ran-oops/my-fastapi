"""Enterprise FastAPI Application with API Versioning.

This module configures the FastAPI application with automatic API versioning.
It supports:
- Semantic versioning (v1, v2)
- Version-specific documentation
- Latest version alias (/api/latest)
- Deprecation warnings for older versions
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.v1 import api_router as v1_router
from app.api.v2 import api_router as v2_router
from app.api.versioning import (
    LATEST_VERSION,
    VERSIONS,
    is_deprecated,
    setup_versioning,
)
from app.core.cache import cache_manager, init_cache
from app.core.config import settings
from app.core.container import init_container
from app.core.eventbus import eventbus
from app.core.events import (
    ORDER_CANCELLED,
    ORDER_CONFIRMED,
    ORDER_SHIPPED,
    TASK_COMPLETED,
    TASK_FAILED,
    USER_PASSWORD_RESET,
    USER_REGISTERED,
)
from app.core.exception_handlers import (
    api_exception_handler,
    generic_exception_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
    validation_exception_handler,
)
from app.core.exceptions import BaseAPIException
from app.core.logging import configure_logging, get_logger
from app.core.middleware import LoggingMiddleware
from app.core.rate_limit import limiter
from app.core.telemetry import setup_telemetry
from app.db.session import SessionFactory, engine
from app.modules.notifications.handlers import notification_handler

# Configure structured logging on startup
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan manager."""
    # Initialize DI container
    init_container()

    # Initialize Redis cache
    try:
        await init_cache()
        logger.info("Cache initialized successfully", event="cache.initialized")
    except Exception as e:
        logger.warning("Cache initialization failed", error=str(e), event="cache.init_failed")

    logger.info(
        "Application starting up",
        event="app.startup",
        app_name=settings.PROJECT_NAME,
        environment=settings.APP_ENV,
        api_versions={v: info.version_string for v, info in VERSIONS.items()},
    )

    async def handle_notification_event(event):
        async with SessionFactory() as session:
            await notification_handler.handle_event(session, event)

    for event_type in [
        ORDER_CONFIRMED,
        ORDER_SHIPPED,
        ORDER_CANCELLED,
        USER_REGISTERED,
        USER_PASSWORD_RESET,
        TASK_COMPLETED,
        TASK_FAILED,
    ]:
        eventbus.subscribe(event_type, lambda e, et=event_type: asyncio.create_task(handle_notification_event(e)))

    yield
    logger.info(
        "Application shutting down",
        event="app.shutdown",
        app_name=settings.PROJECT_NAME,
    )
    await engine.dispose()
    # Close cache connection
    await cache_manager.close()


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise FastAPI Project with Automatic API Versioning.\n\n"
    "## API Versions\n\n"
    "- **v1**: Deprecated, sunset date 2025-12-31\n"
    "- **v2**: Current stable version\n"
    "- **latest**: Points to v2\n\n"
    "See `/versions` endpoint for version details.",
    version=VERSIONS[LATEST_VERSION].version_string,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
app.state.limiter = limiter

# Add logging middleware first to capture trace ID for all requests
app.add_middleware(LoggingMiddleware)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Setup API versioning
version_manager = setup_versioning(app)

# Register v1 routes (deprecated but supported)
version_manager.register_version(
    router=v1_router,
    version=1,
    prefix="/api/v1",
)

# Register v2 routes (current stable)
version_manager.register_version(
    router=v2_router,
    version=2,
    prefix="/api/v2",
)

# Register /api/latest alias
version_manager.register_latest_alias(version=2)

# Add exception handlers
app.add_exception_handler(BaseAPIException, api_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Enterprise FastAPI Project",
        "description": "Enterprise API with automatic versioning support",
        "versions": {
            "current": f"/api/v{LATEST_VERSION}",
            "latest": "/api/latest",
            "v1": {
                "url": "/api/v1",
                "docs": "/api/v1/docs",
                "status": "deprecated",
                "deprecated_since": "2025-01-01",
                "sunset_date": "2025-12-31",
            },
            "v2": {
                "url": "/api/v2",
                "docs": "/api/v2/docs",
                "status": "current",
            },
        },
        "migration_guide": "https://docs.example.com/migration/v1-to-v2",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "api_version": VERSIONS[LATEST_VERSION].version_string,
        "api_latest": f"v{LATEST_VERSION}",
    }


@app.get("/health/ready", tags=["health"])
async def readiness_check():
    """Readiness probe for Kubernetes/Container orchestration."""
    db_status = {}
    cache_status = {}
    overall_status = "ready"

    async def check_db(name: str, db_engine) -> bool:
        try:
            async with db_engine.connect() as conn:
                from sqlalchemy import text

                await conn.execute(text("SELECT 1"))
                db_status[name] = "connected"
                return True
        except Exception as e:
            db_status[name] = f"error: {e!s}"
            return False

    db_ok = await check_db("database", engine)

    # Check cache health if available
    try:
        cache_ok = await cache_manager.health_check()
        cache_status["redis"] = "connected" if cache_ok else "unavailable"
    except Exception as e:
        cache_status["redis"] = f"error: {e!s}"
        cache_ok = False

    if not db_ok:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "databases": db_status,
        "cache": cache_status,
        "timestamp": datetime.now(UTC).isoformat(),
        "api_version": VERSIONS[LATEST_VERSION].version_string,
    }


@app.get("/health/version-info", tags=["health"])
async def version_health_check():
    """Health check with version deprecation status."""
    deprecated_versions = [v for v, info in VERSIONS.items() if info.status == "deprecated"]
    current_versions = [v for v, info in VERSIONS.items() if info.status == "current"]

    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "versions": {
            "total": len(VERSIONS),
            "current": current_versions,
            "deprecated": deprecated_versions,
            "latest": LATEST_VERSION,
        },
    }
