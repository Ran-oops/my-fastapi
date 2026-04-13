"""Structured logging configuration using structlog.

This module configures structlog for JSON structured logging in production
and pretty console output in development.
"""

import logging
import logging.config
import sys
from typing import Any

import structlog
from structlog.processors import JSONRenderer
from structlog.stdlib import filter_by_level

from app.core.config import settings


def add_trace_id(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Add trace_id to event dict if available.

    Compatible with OpenTelemetry trace context.
    """
    from contextvars import ContextVar

    trace_id_var = ContextVar("trace_id", default=None)
    trace_id = trace_id_var.get(None)
    if trace_id:
        event_dict["trace_id"] = trace_id
    return event_dict


def add_logger_name(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Add logger name to event dict."""
    event_dict["logger"] = event_dict.get("logger", logger.name)
    return event_dict


def rename_message_to_event(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Rename 'event' to 'message' for consistency with traditional logging."""
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


def lowercase_log_level(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Convert log level to lowercase."""
    if "level" in event_dict:
        event_dict["level"] = event_dict["level"].lower()
    return event_dict


def get_structlog_processors() -> list:
    """Get structlog processors based on environment."""
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_trace_id,
        add_logger_name,
        structlog.stdlib.ExtraAdder(),
        filter_by_level,
    ]

    if settings.APP_ENV == "production":
        processors.extend(
            [
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                lowercase_log_level,
                rename_message_to_event,
                JSONRenderer(ensure_ascii=False),
            ]
        )
    else:
        processors.extend(
            [
                structlog.processors.ExceptionPrettyPrinter(),
                structlog.dev.ConsoleRenderer(
                    colors=True,
                    exception_formatter=structlog.dev.rich_traceback,
                ),
            ]
        )

    return processors


def get_stdlib_processors() -> list:
    """Get stdlib logging processors for wrapping."""
    return [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]


def configure_logging() -> None:
    """Configure structured logging for the application.

    Sets up both structlog and stdlib logging with:
    - JSON format for production
    - Pretty console format for development
    - Trace ID support for OpenTelemetry compatibility
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    stdlib_handlers = ["console"] if settings.APP_ENV != "production" else ["json_console"]

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "fmt": "%(timestamp)s %(level)s %(name)s %(message)s",
                    "timestamp": True,
                },
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "standard",
                    "stream": "ext://sys.stdout",
                },
                "json_console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": log_level,
                "handlers": stdlib_handlers,
            },
            "loggers": {
                "uvicorn": {
                    "level": log_level,
                    "handlers": stdlib_handlers,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": log_level,
                    "handlers": stdlib_handlers,
                    "propagate": False,
                },
                "sqlalchemy.engine": {
                    "level": "WARNING",
                    "handlers": stdlib_handlers,
                    "propagate": False,
                },
                "celery": {
                    "level": log_level,
                    "handlers": stdlib_handlers,
                    "propagate": False,
                },
            },
        }
    )

    structlog.configure(
        processors=get_structlog_processors(),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory()
        if settings.APP_ENV != "production"
        else structlog.BytesLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name, defaults to caller's module name.

    Returns:
        A configured structlog BoundLogger.
    """
    return structlog.get_logger(name)


# Global trace_id context var for OpenTelemetry compatibility
_trace_id: Any = None


def set_trace_id(trace_id: str | None) -> None:
    """Set the current trace ID in context.

    Args:
        trace_id: The trace ID to set, or None to clear.
    """
    import contextvars

    global _trace_id
    _trace_id = trace_id
    trace_id_var = contextvars.ContextVar("trace_id", default=None)
    trace_id_var.set(trace_id)


def get_trace_id() -> str | None:
    """Get the current trace ID from context.

    Returns:
        The current trace ID or None if not set.
    """
    return _trace_id


# Configure logging on module import
configure_logging()
