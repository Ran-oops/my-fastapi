"""FastAPI middleware for structured logging and trace context.

Provides middleware to inject trace IDs and log request/response data.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger, set_trace_id

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add trace IDs and log request/response info."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract trace ID from request headers
        trace_id = request.headers.get("X-Request-ID") or request.headers.get("X-Trace-ID")
        if not trace_id:
            trace_id = str(uuid.uuid4())

        # Set trace ID in context
        set_trace_id(trace_id)

        # Add trace ID to request state for access in endpoints
        request.state.trace_id = trace_id

        start_time = time.perf_counter()

        # Log request
        logger.info(
            "Request started",
            event="http.request.start",
            method=request.method,
            path=request.url.path,
            trace_id=trace_id,
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Add trace ID to response headers
            response.headers["X-Trace-ID"] = trace_id

            # Log response
            logger.info(
                "Request completed",
                event="http.request.complete",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                trace_id=trace_id,
            )

            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log error
            logger.error(
                "Request failed",
                event="http.request.error",
                method=request.method,
                path=request.url.path,
                error_type=type(exc).__name__,
                error_message=str(exc),
                duration_ms=round(duration_ms, 2),
                trace_id=trace_id,
                exc_info=True,
            )
            raise

        finally:
            # Clear trace ID from context
            set_trace_id(None)
