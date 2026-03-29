from fastapi import HTTPException, status
from typing import Any


class BaseAPIException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: dict | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        if headers is None:
            headers = {}
        self.error_code = error_code
        self.details = details or {}
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundException(BaseAPIException):
    """Resource not found"""

    def __init__(self, detail: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code=error_code,
        )


class ConflictException(BaseAPIException):
    """Resource conflict"""

    def __init__(self, detail: str = "Resource already exists", error_code: str = "CONFLICT"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code=error_code,
        )


class UnauthorizedException(BaseAPIException):
    """Unauthorized access"""

    def __init__(self, detail: str = "Unauthorized", error_code: str = "UNAUTHORIZED"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code,
        )


class ForbiddenException(BaseAPIException):
    """Forbidden access"""

    def __init__(self, detail: str = "Forbidden", error_code: str = "FORBIDDEN"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code,
        )


class ValidationException(BaseAPIException):
    """Validation error"""

    def __init__(
        self,
        detail: str = "Validation error",
        error_code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
            error_code=error_code,
            details=details,
        )


class BadRequestException(BaseAPIException):
    """Bad request error"""

    def __init__(
        self,
        detail: str = "Bad request",
        error_code: str = "BAD_REQUEST",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code,
            details=details,
        )


class RateLimitException(BaseAPIException):
    """Rate limit exceeded"""

    def __init__(self, detail: str = "Rate limit exceeded", retry_after: int = 60):
        headers = {"Retry-After": str(retry_after)}
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
            error_code="RATE_LIMIT_EXCEEDED",
        )


class ServiceUnavailableException(BaseAPIException):
    """Service temporarily unavailable"""

    def __init__(self, detail: str = "Service temporarily unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="SERVICE_UNAVAILABLE",
        )
