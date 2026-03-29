import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import BaseAPIException


logger = logging.getLogger(__name__)


async def api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """Custom exception handler for API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "message": exc.detail,
                "code": exc.error_code,
                **({"details": exc.details} if exc.details else {}),
            },
        },
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "error": {
                "message": "Validation error",
                "code": "VALIDATION_ERROR",
                "details": {"errors": errors},
            },
        },
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Handler for database integrity errors."""
    logger.warning(f"Integrity error on {request.url}: {exc!s}")

    error_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)

    if "UNIQUE constraint" in error_msg or "duplicate key" in error_msg.lower():
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "error": {
                    "message": "A record with this information already exists",
                    "code": "DUPLICATE_ENTRY",
                },
            },
        )
    elif "FOREIGN KEY" in error_msg or "foreign key constraint" in error_msg.lower():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "message": "Referenced record does not exist",
                    "code": "FOREIGN_KEY_VIOLATION",
                },
            },
        )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "message": "Database constraint violation",
                "code": "CONSTRAINT_VIOLATION",
            },
        },
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handler for general SQLAlchemy errors."""
    logger.error(f"Database error on {request.url}: {exc!s}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "message": "A database error occurred",
                "code": "DATABASE_ERROR",
            },
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unexpected exceptions."""
    logger.exception(f"Unexpected error on {request.url}: {exc!s}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "message": "An unexpected error occurred",
                "code": "INTERNAL_ERROR",
            },
        },
    )
