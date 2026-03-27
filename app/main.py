import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.core.eventbus import eventbus
from app.core.events import (
    ORDER_CONFIRMED,
    ORDER_SHIPPED,
    ORDER_CANCELLED,
    USER_REGISTERED,
    USER_PASSWORD_RESET,
    TASK_COMPLETED,
    TASK_FAILED,
)
from app.db.session import business_engine, config_engine, user_engine, UserSessionFactory
from app.modules.notifications.handlers import notification_handler


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Application starting up...")

    async def handle_notification_event(event):
        async with UserSessionFactory() as session:
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
    await user_engine.dispose()
    await business_engine.dispose()
    await config_engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500},
    )


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

    async def check_db(name: str, engine) -> bool:
        try:
            async with engine.connect() as conn:
                from sqlalchemy import text

                await conn.execute(text("SELECT 1"))
            db_status[name] = "connected"
            return True
        except Exception as e:
            db_status[name] = f"error: {e!s}"
            return False

    user_ok = await check_db("user_db", user_engine)
    business_ok = await check_db("business_db", business_engine)
    config_ok = await check_db("config_db", config_engine)

    if not all([user_ok, business_ok, config_ok]):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "databases": db_status,
        "timestamp": datetime.now(UTC).isoformat(),
    }
