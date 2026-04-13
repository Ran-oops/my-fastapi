"""Rate limiting configuration and middleware."""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

# Initialize limiter with key function
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT] if hasattr(settings, "RATE_LIMIT_DEFAULT") else None,
    storage_uri=settings.REDIS_URL if hasattr(settings, "REDIS_URL") else "memory://",
)


async def rate_limit_exceeded_handler(request, exc):
    """Handler for rate limit exceeded exceptions."""
    from fastapi import Request
    from starlette.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "rate_limit_exceeded",
                "message": "Too many requests, please try again later.",
                "retry_after": getattr(exc, "retry_after", 60),
            },
        },
    )
