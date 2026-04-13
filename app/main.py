import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.v1 import api_router
from app.core.config import settings
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
from app.core.rate_limit import limiter
from app.db.session import SessionFactory, engine
from app.modules.notifications.handlers import notification_handler


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Application starting up...")

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
    logger.info("Application shutting down...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)
app.state.limiter = limiter

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

app.add_exception_handler(BaseAPIException, api_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Enterprise FastAPI Project",
        "docs": f"{settings.API_V1_STR}/docs",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
    }


@app.get("/health/ready")
async def readiness_check():
    db_status = {}
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

    if not db_ok:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "databases": db_status,
        "timestamp": datetime.now(UTC).isoformat(),
    }
