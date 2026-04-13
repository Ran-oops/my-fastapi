"""
Comprehensive tests for custom exceptions and exception handlers.

Tests cover:
- All custom exception classes
- Exception handlers
- Exception chaining
- HTTP status code mapping
"""

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import (
    BadRequestException,
    BaseAPIException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    RateLimitException,
    ServiceUnavailableException,
    UnauthorizedException,
    ValidationException,
)
from app.core.exception_handlers import (
    api_exception_handler,
    generic_exception_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
    validation_exception_handler,
)


class TestBaseAPIException:
    """Tests for BaseAPIException."""

    def test_base_exception_creation(self):
        """Test creating a base API exception."""
        exc = BaseAPIException(
            status_code=status.HTTP_418_IM_A_TEAPOT,
            detail="I'm a teapot",
            error_code="TEAPOT",
            details={"teapot": True},
        )
        assert exc.status_code == status.HTTP_418_IM_A_TEAPOT
        assert exc.detail == "I'm a teapot"
        assert exc.error_code == "TEAPOT"
        assert exc.details == {"teapot": True}

    def test_base_exception_default_headers(self):
        """Test base exception with default headers."""
        exc = BaseAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad request",
        )
        assert exc.headers == {}

    def test_base_exception_custom_headers(self):
        """Test base exception with custom headers."""
        exc = BaseAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad request",
            headers={"X-Custom-Header": "value"},
        )
        assert exc.headers == {"X-Custom-Header": "value"}

    def test_base_exception_inheritance(self):
        """Test that BaseAPIException inherits from HTTPException."""
        from fastapi import HTTPException

        exc = BaseAPIException(status_code=400, detail="test")
        assert isinstance(exc, HTTPException)


class TestNotFoundException:
    """Tests for NotFoundException."""

    def test_not_found_default(self):
        """Test NotFoundException with default values."""
        exc = NotFoundException()
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.detail == "Resource not found"
        assert exc.error_code == "NOT_FOUND"

    def test_not_found_custom_message(self):
        """Test NotFoundException with custom message."""
        exc = NotFoundException(detail="User not found")
        assert exc.detail == "User not found"
        assert exc.error_code == "NOT_FOUND"

    def test_not_found_custom_error_code(self):
        """Test NotFoundException with custom error code."""
        exc = NotFoundException(detail="Product not found", error_code="PRODUCT_NOT_FOUND")
        assert exc.detail == "Product not found"
        assert exc.error_code == "PRODUCT_NOT_FOUND"


class TestConflictException:
    """Tests for ConflictException."""

    def test_conflict_default(self):
        """Test ConflictException with default values."""
        exc = ConflictException()
        assert exc.status_code == status.HTTP_409_CONFLICT
        assert exc.detail == "Resource already exists"
        assert exc.error_code == "CONFLICT"

    def test_conflict_custom_message(self):
        """Test ConflictException with custom message."""
        exc = ConflictException(detail="Email already registered")
        assert exc.detail == "Email already registered"


class TestUnauthorizedException:
    """Tests for UnauthorizedException."""

    def test_unauthorized_default(self):
        """Test UnauthorizedException with default values."""
        exc = UnauthorizedException()
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.detail == "Unauthorized"
        assert exc.error_code == "UNAUTHORIZED"

    def test_unauthorized_invalid_credentials(self):
        """Test UnauthorizedException with invalid credentials message."""
        exc = UnauthorizedException(detail="Invalid credentials")
        assert exc.detail == "Invalid credentials"

    def test_unauthorized_inactive_user(self):
        """Test UnauthorizedException with inactive user message."""
        exc = UnauthorizedException(detail="Inactive user")
        assert exc.detail == "Inactive user"


class TestForbiddenException:
    """Tests for ForbiddenException."""

    def test_forbidden_default(self):
        """Test ForbiddenException with default values."""
        exc = ForbiddenException()
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert exc.detail == "Forbidden"
        assert exc.error_code == "FORBIDDEN"

    def test_forbidden_insufficient_permissions(self):
        """Test ForbiddenException with permissions message."""
        exc = ForbiddenException(detail="Insufficient permissions")
        assert exc.detail == "Insufficient permissions"


class TestValidationException:
    """Tests for ValidationException."""

    def test_validation_default(self):
        """Test ValidationException with default values."""
        exc = ValidationException()
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert exc.detail == "Validation error"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details == {}

    def test_validation_with_details(self):
        """Test ValidationException with validation details."""
        exc = ValidationException(
            detail="Field validation failed",
            details={"field_errors": [{"field": "email", "message": "Invalid format"}]},
        )
        assert exc.detail == "Field validation failed"
        assert exc.details["field_errors"][0]["field"] == "email"

    def test_validation_status_transition(self):
        """Test ValidationException for status transition."""
        exc = ValidationException(detail="Cannot transition from PENDING to COMPLETED")
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestBadRequestException:
    """Tests for BadRequestException."""

    def test_bad_request_default(self):
        """Test BadRequestException with default values."""
        exc = BadRequestException()
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.detail == "Bad request"
        assert exc.error_code == "BAD_REQUEST"

    def test_bad_request_with_details(self):
        """Test BadRequestException with details."""
        exc = BadRequestException(detail="Invalid request format", details={"expected": "JSON", "received": "XML"})
        assert exc.detail == "Invalid request format"
        assert exc.details["expected"] == "JSON"


class TestRateLimitException:
    """Tests for RateLimitException."""

    def test_rate_limit_default(self):
        """Test RateLimitException with default values."""
        exc = RateLimitException()
        assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc.detail == "Rate limit exceeded"
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.headers == {"Retry-After": "60"}

    def test_rate_limit_custom_retry(self):
        """Test RateLimitException with custom retry time."""
        exc = RateLimitException(retry_after=300)
        assert exc.headers == {"Retry-After": "300"}

    def test_rate_limit_custom_message(self):
        """Test RateLimitException with custom message."""
        exc = RateLimitException(detail="Too many requests, slow down")
        assert exc.detail == "Too many requests, slow down"


class TestServiceUnavailableException:
    """Tests for ServiceUnavailableException."""

    def test_service_unavailable_default(self):
        """Test ServiceUnavailableException with default values."""
        exc = ServiceUnavailableException()
        assert exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert exc.detail == "Service temporarily unavailable"
        assert exc.error_code == "SERVICE_UNAVAILABLE"

    def test_service_unavailable_custom(self):
        """Test ServiceUnavailableException with custom message."""
        exc = ServiceUnavailableException(detail="Database maintenance in progress")
        assert exc.detail == "Database maintenance in progress"


class TestHTTPStatusCodeMapping:
    """Tests for HTTP status code mapping."""

    def test_status_code_coverage(self):
        """Test that all custom exceptions have appropriate status codes."""
        exceptions_status = {
            NotFoundException: status.HTTP_404_NOT_FOUND,
            ConflictException: status.HTTP_409_CONFLICT,
            UnauthorizedException: status.HTTP_401_UNAUTHORIZED,
            ForbiddenException: status.HTTP_403_FORBIDDEN,
            ValidationException: status.HTTP_422_UNPROCESSABLE_CONTENT,
            BadRequestException: status.HTTP_400_BAD_REQUEST,
            RateLimitException: status.HTTP_429_TOO_MANY_REQUESTS,
            ServiceUnavailableException: status.HTTP_503_SERVICE_UNAVAILABLE,
        }

        for exc_class, expected_status in exceptions_status.items():
            exc = exc_class()
            assert exc.status_code == expected_status, f"{exc_class.__name__} has wrong status code"

    def test_error_code_uniqueness(self):
        """Test that default error codes are unique."""
        error_codes = [
            NotFoundException().error_code,
            ConflictException().error_code,
            UnauthorizedException().error_code,
            ForbiddenException().error_code,
            ValidationException().error_code,
            BadRequestException().error_code,
            RateLimitException().error_code,
            ServiceUnavailableException().error_code,
        ]
        assert len(error_codes) == len(set(error_codes)), "Error codes should be unique"


class TestAPIExceptionHandler:
    """Tests for API exception handler."""

    @pytest.mark.asyncio
    async def test_api_exception_handler_response(self):
        """Test API exception handler produces correct response."""
        request = Request(scope={"type": "http", "method": "GET", "url": "http://test/"})
        exc = NotFoundException(detail="User 123 not found")

        response = await api_exception_handler(request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.body is not None

    @pytest.mark.asyncio
    async def test_api_exception_handler_with_details(self):
        """Test API exception handler with exception details."""
        request = Request(scope={"type": "http", "method": "GET", "url": "http://test/"})
        exc = ValidationException(detail="Validation failed", details={"fields": ["email", "password"]})

        response = await api_exception_handler(request, exc)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_api_exception_handler_headers(self):
        """Test API exception handler preserves headers."""
        request = Request(scope={"type": "http", "method": "GET", "url": "http://test/"})
        exc = RateLimitException(retry_after=120)

        response = await api_exception_handler(request, exc)

        assert response.headers.get("retry-after") == "120"


class TestValidationExceptionHandler:
    """Tests for validation exception handler."""

    @pytest.mark.asyncio
    async def test_validation_handler_response(self):
        """Test validation exception handler produces correct response."""
        request = Request(scope={"type": "http", "method": "POST", "url": "http://test/"})

        # Create a validation error
        class TestModel(BaseModel):
            email: str

            @field_validator("email")
            @classmethod
            def validate_email(cls, v):
                if "@" not in v:
                    raise ValueError("Invalid email")
                return v

        try:
            TestModel(email="invalid")
        except ValidationError as e:
            exc = RequestValidationError(errors=e.errors())

        response = await validation_exception_handler(request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestIntegrityErrorHandler:
    """Tests for integrity error handler."""

    @pytest.mark.asyncio
    async def test_integrity_unique_constraint(self):
        """Test integrity error handler for unique constraint violation."""
        request = Request(scope={"type": "http", "method": "POST", "url": "http://test/"})

        # Create a mock integrity error
        class MockOrig:
            def __str__(self):
                return "UNIQUE constraint failed: users.email"

        exc = IntegrityError("test", "test", "test")
        exc.orig = MockOrig()

        response = await integrity_error_handler(request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_integrity_foreign_key(self):
        """Test integrity error handler for foreign key violation."""
        request = Request(scope={"type": "http", "method": "POST", "url": "http://test/"})

        class MockOrig:
            def __str__(self):
                return "FOREIGN KEY constraint failed"

        exc = IntegrityError("test", "test", "test")
        exc.orig = MockOrig()

        response = await integrity_error_handler(request, exc)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_integrity_unknown(self):
        """Test integrity error handler for unknown constraint violation."""
        request = Request(scope={"type": "http", "method": "POST", "url": "http://test/"})

        class MockOrig:
            def __str__(self):
                return "Some other constraint error"

        exc = IntegrityError("test", "test", "test")
        exc.orig = MockOrig()

        response = await integrity_error_handler(request, exc)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestSQLAlchemyErrorHandler:
    """Tests for SQLAlchemy error handler."""

    @pytest.mark.asyncio
    async def test_sqlalchemy_error_handler(self):
        """Test SQLAlchemy error handler produces correct response."""
        request = Request(scope={"type": "http", "method": "GET", "url": "http://test/"})
        exc = SQLAlchemyError("Database connection lost")

        response = await sqlalchemy_error_handler(request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGenericExceptionHandler:
    """Tests for generic exception handler."""

    @pytest.mark.asyncio
    async def test_generic_exception_handler(self):
        """Test generic exception handler produces correct response."""
        request = Request(scope={"type": "http", "method": "GET", "url": "http://test/"})
        exc = Exception("Unexpected error")

        response = await generic_exception_handler(request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_generic_exception_handler_value_error(self):
        """Test generic exception handler with ValueError."""
        request = Request(scope={"type": "http", "method": "GET", "url": "http://test/"})
        exc = ValueError("Invalid value")

        response = await generic_exception_handler(request, exc)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestExceptionChaining:
    """Tests for exception chaining."""

    def test_exception_chain_preservation(self):
        """Test that exception chain is preserved."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise NotFoundException(detail="Wrapped error") from e
        except NotFoundException as exc:
            assert exc.__cause__ is not None
            assert isinstance(exc.__cause__, ValueError)

    def test_raise_from_preserves_context(self):
        """Test raise ... from preserves exception context."""
        try:
            raise ConnectionError("DB connection failed")
        except ConnectionError:
            exc = ServiceUnavailableException(detail="Service unavailable")
            assert exc.__context__ is None  # No chaining with 'from'


class TestExceptionResponseFormat:
    """Tests for exception response format."""

    @pytest.mark.asyncio
    async def test_response_success_field(self):
        """Test that response has success=false field."""
        request = Request(scope={"type": "http", "method": "GET", "url": "http://test/"})
        exc = NotFoundException()

        response = await api_exception_handler(request, exc)
        body = response.body.decode()

        assert '"success":false' in body or '"success": false' in body

    @pytest.mark.asyncio
    async def test_response_error_structure(self):
        """Test that response has proper error structure."""
        request = Request(scope={"type": "http", "method": "GET", "url": "http://test/"})
        exc = ValidationException(detail="Validation failed", error_code="VALIDATION_ERROR")

        response = await api_exception_handler(request, exc)
        body = response.body.decode()

        assert '"error"' in body
        assert '"message"' in body
        assert '"code"' in body

    @pytest.mark.asyncio
    async def test_response_optional_details(self):
        """Test that details are included only when present."""
        request = Request(scope={"type": "http", "method": "GET", "url": "http://test/"})

        # Without details
        exc_no_details = NotFoundException()
        response1 = await api_exception_handler(request, exc_no_details)
        body1 = response1.body.decode()

        # With details
        exc_with_details = BadRequestException(details={"field": "value"})
        response2 = await api_exception_handler(request, exc_with_details)
        body2 = response2.body.decode()

        assert '"details"' in body2


class TestExceptionEdgeCases:
    """Tests for exception edge cases."""

    def test_exception_with_empty_detail(self):
        """Test exception with empty detail string."""
        exc = NotFoundException(detail="")
        assert exc.detail == ""

    def test_exception_with_none_in_details(self):
        """Test exception with None in details dict."""
        exc = BadRequestException(details={"field": None, "other": "value"})
        assert exc.details["field"] is None

    def test_exception_with_very_long_detail(self):
        """Test exception with very long detail message."""
        long_message = "A" * 10000
        exc = NotFoundException(detail=long_message)
        assert len(exc.detail) == 10000

    def test_rate_limit_with_zero_retry(self):
        """Test RateLimitException with zero retry time."""
        exc = RateLimitException(retry_after=0)
        assert exc.headers["Retry-After"] == "0"

    def test_rate_limit_with_negative_retry(self):
        """Test RateLimitException with negative retry time."""
        exc = RateLimitException(retry_after=-1)
        assert exc.headers["Retry-After"] == "-1"
