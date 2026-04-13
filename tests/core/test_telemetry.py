"""Tests for OpenTelemetry distributed tracing configuration.

This module tests:
- Tracer provider initialization
- Span creation and attributes
- @traced decorator functionality
- span_context context manager
- Resource attribute creation
- Manual tracing utilities
"""

import asyncio
from contextlib import contextmanager
from functools import wraps
from unittest.mock import MagicMock, Mock, patch, AsyncMock

import pytest
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode

from app.core.telemetry import (
    add_event,
    add_span_attributes,
    create_otlp_exporter,
    create_resource,
    get_tracer,
    instrument_celery,
    instrument_fastapi,
    instrument_logging,
    instrument_redis,
    instrument_sqlalchemy,
    set_span_error,
    setup_telemetry,
    setup_tracer_provider,
    span_context,
    traced,
)


class TestTracerProvider:
    """Tests for tracer provider initialization."""

    def test_setup_tracer_provider_returns_provider(self):
        """Test that setup_tracer_provider returns a TracerProvider instance."""
        with patch("app.core.telemetry.trace.set_tracer_provider") as mock_set:
            provider = setup_tracer_provider()

            assert isinstance(provider, TracerProvider)
            mock_set.assert_called_once_with(provider)

    def test_setup_tracer_provider_creates_resource(self):
        """Test that tracer provider is created with resource attributes."""
        with (
            patch("app.core.telemetry.create_resource") as mock_create_resource,
            patch("app.core.telemetry.trace.set_tracer_provider"),
        ):
            mock_resource = MagicMock()
            mock_create_resource.return_value = mock_resource

            provider = setup_tracer_provider()

            # Verify resource was created and used
            mock_create_resource.assert_called_once()

    def test_setup_tracer_provider_with_otlp_exporter(self):
        """Test tracer provider with OTLP exporter."""
        with (
            patch.dict("os.environ", {"OTEL_TRACES_EXPORTER": "otlp"}),
            patch("app.core.telemetry.create_otlp_exporter") as mock_create_otlp,
            patch("app.core.telemetry.BatchSpanProcessor") as mock_processor,
            patch("app.core.telemetry.trace.set_tracer_provider"),
        ):
            mock_exporter = MagicMock()
            mock_create_otlp.return_value = mock_exporter

            provider = setup_tracer_provider()

            mock_create_otlp.assert_called_once()
            mock_processor.assert_called_once()

    def test_setup_tracer_provider_with_console_exporter(self):
        """Test tracer provider with console exporter."""
        with (
            patch.dict("os.environ", {"OTEL_TRACES_EXPORTER": "console"}),
            patch("app.core.telemetry.ConsoleSpanExporter") as mock_console,
            patch("app.core.telemetry.BatchSpanProcessor") as mock_processor,
            patch("app.core.telemetry.trace.set_tracer_provider"),
        ):
            mock_exporter = MagicMock()
            mock_console.return_value = mock_exporter

            provider = setup_tracer_provider()

            mock_console.assert_called_once()
            mock_processor.assert_called_once()

    def test_setup_tracer_provider_with_none_exporter(self):
        """Test tracer provider with no exporter (disabled)."""
        with (
            patch.dict("os.environ", {"OTEL_TRACES_EXPORTER": "none"}),
            patch("app.core.telemetry.trace.set_tracer_provider"),
        ):
            provider = setup_tracer_provider()

            assert isinstance(provider, TracerProvider)

    def test_get_tracer_returns_tracer(self):
        """Test that get_tracer returns a tracer instance."""
        with patch("app.core.telemetry.trace.get_tracer") as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_get_tracer.return_value = mock_tracer

            tracer = get_tracer()

            assert tracer == mock_tracer
            mock_get_tracer.assert_called_once_with("app.core.telemetry")

    def test_get_tracer_caches_instance(self):
        """Test that get_tracer caches the tracer instance."""
        with patch("app.core.telemetry.trace.get_tracer") as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_get_tracer.return_value = mock_tracer

            # First call
            tracer1 = get_tracer()
            # Second call should return cached instance
            tracer2 = get_tracer()

            # Should only call get_tracer once since it's cached
            mock_get_tracer.assert_called_once()
            assert tracer1 == tracer2


class TestResourceAttributes:
    """Tests for resource attribute creation."""

    def test_create_resource_returns_resource(self):
        """Test that create_resource returns a Resource instance."""
        with patch.dict("os.environ", {}, clear=True):
            resource = create_resource()

            assert isinstance(resource, Resource)

    def test_create_resource_with_service_name(self):
        """Test that resource contains service name."""
        with patch.dict("os.environ", {"OTEL_SERVICE_NAME": "test-service"}):
            resource = create_resource()

            assert resource.attributes.get("service.name") == "test-service"

    def test_create_resource_with_service_version(self):
        """Test that resource contains service version."""
        with patch.dict("os.environ", {"OTEL_SERVICE_VERSION": "2.0.0"}):
            resource = create_resource()

            assert resource.attributes.get("service.version") == "2.0.0"

    def test_create_resource_with_deployment_environment(self):
        """Test that resource contains deployment environment."""
        with patch.dict("os.environ", {"OTEL_ENVIRONMENT": "staging"}):
            resource = create_resource()

            assert resource.attributes.get("deployment.environment") == "staging"

    def test_create_resource_with_service_namespace(self):
        """Test that resource contains service namespace."""
        with patch.dict("os.environ", {"OTEL_SERVICE_NAMESPACE": "my-namespace"}):
            resource = create_resource()

            assert resource.attributes.get("service.namespace") == "my-namespace"

    def test_create_resource_with_host_name(self):
        """Test that resource contains host name."""
        with patch.dict("os.environ", {"HOSTNAME": "test-host"}):
            resource = create_resource()

            assert resource.attributes.get("host.name") == "test-host"

    def test_create_resource_defaults_from_settings(self):
        """Test that resource uses settings when env vars not set."""
        with patch.dict("os.environ", {}, clear=True), patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.PROJECT_NAME = "Test Project"
            mock_settings.APP_ENV = "development"

            resource = create_resource()

            # Service name should be derived from PROJECT_NAME
            assert resource.attributes.get("service.name") == "test_project"
            assert resource.attributes.get("deployment.environment") == "development"


class TestOTLPExporter:
    """Tests for OTLP exporter creation."""

    def test_create_otlp_exporter_with_defaults(self):
        """Test OTLP exporter creation with default settings."""
        with patch("app.core.telemetry.OTLPSpanExporter") as mock_exporter:
            mock_instance = MagicMock()
            mock_exporter.return_value = mock_instance

            result = create_otlp_exporter()

            mock_exporter.assert_called_once_with(
                endpoint="http://localhost:4317",
                insecure=True,
            )
            assert result == mock_instance

    def test_create_otlp_exporter_with_custom_endpoint(self):
        """Test OTLP exporter with custom endpoint."""
        with (
            patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://otel:4317"}),
            patch("app.core.telemetry.OTLPSpanExporter") as mock_exporter,
        ):
            mock_instance = MagicMock()
            mock_exporter.return_value = mock_instance

            result = create_otlp_exporter()

            mock_exporter.assert_called_once_with(
                endpoint="http://otel:4317",
                insecure=True,
            )

    def test_create_otlp_exporter_with_secure_connection(self):
        """Test OTLP exporter with secure connection."""
        with (
            patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_INSECURE": "false"}),
            patch("app.core.telemetry.OTLPSpanExporter") as mock_exporter,
        ):
            mock_instance = MagicMock()
            mock_exporter.return_value = mock_instance

            result = create_otlp_exporter()

            mock_exporter.assert_called_once_with(
                endpoint="http://localhost:4317",
                insecure=False,
            )

    def test_create_otlp_exporter_handles_exception(self):
        """Test OTLP exporter handles creation exceptions."""
        with patch("app.core.telemetry.OTLPSpanExporter") as mock_exporter:
            mock_exporter.side_effect = Exception("Connection failed")

            result = create_otlp_exporter()

            assert result is None


class TestTracedDecorator:
    """Tests for @traced decorator functionality."""

    @pytest.mark.asyncio
    async def test_traced_decorator_async_function(self):
        """Test @traced decorator on async function."""
        with patch("app.core.telemetry.get_tracer") as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
            mock_get_tracer.return_value = mock_tracer

            @traced(span_name="test_operation", attributes={"custom": "value"})
            async def async_func(arg1, arg2):
                return f"result: {arg1}, {arg2}"

            result = await async_func("a", "b")

            assert result == "result: a, b"
            mock_tracer.start_as_current_span.assert_called_once_with("test_operation")
            mock_span.set_attribute.assert_any_call("custom", "value")

    def test_traced_decorator_sync_function(self):
        """Test @traced decorator on sync function."""
        with patch("app.core.telemetry.get_tracer") as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
            mock_get_tracer.return_value = mock_tracer

            @traced(span_name="sync_operation")
            def sync_func(value):
                return value * 2

            result = sync_func(5)

            assert result == 10
            mock_tracer.start_as_current_span.assert_called_once_with("sync_operation")

    @pytest.mark.asyncio
    async def test_traced_decorator_records_exception(self):
        """Test that @traced decorator records exceptions."""
        with patch("app.core.telemetry.get_tracer") as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
            mock_get_tracer.return_value = mock_tracer

            @traced(span_name="failing_operation")
            async def failing_func():
                raise ValueError("Test error")

            with pytest.raises(ValueError, match="Test error"):
                await failing_func()

            mock_span.record_exception.assert_called_once()
            mock_span.set_status.assert_called_once()

    def test_traced_decorator_uses_function_name_as_default(self):
        """Test that @traced uses function name when span_name not provided."""
        with patch("app.core.telemetry.get_tracer") as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
            mock_get_tracer.return_value = mock_tracer

            @traced()
            def my_custom_function():
                return "done"

            my_custom_function()

            mock_tracer.start_as_current_span.assert_called_once_with("my_custom_function")

    def test_traced_decorator_preserves_function_metadata(self):
        """Test that @traced preserves function metadata."""

        @traced()
        def my_function():
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestSpanContext:
    """Tests for span_context context manager."""

    def test_span_context_creates_span(self):
        """Test that span_context creates a span."""
        with patch("app.core.telemetry.get_tracer") as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
            mock_get_tracer.return_value = mock_tracer

            with span_context("manual_span", {"key": "value"}) as span:
                pass

            mock_tracer.start_as_current_span.assert_called_once_with("manual_span")
            mock_span.set_attribute.assert_called_once_with("key", "value")

    def test_span_context_without_attributes(self):
        """Test span_context without attributes."""
        with patch("app.core.telemetry.get_tracer") as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
            mock_get_tracer.return_value = mock_tracer

            with span_context("simple_span") as span:
                pass

            mock_tracer.start_as_current_span.assert_called_once_with("simple_span")
            # Should not call set_attribute when no attributes
            mock_span.set_attribute.assert_not_called()

    def test_span_context_yields_span(self):
        """Test that span_context yields the span for manual attribute setting."""
        with patch("app.core.telemetry.get_tracer") as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
            mock_get_tracer.return_value = mock_tracer

            with span_context("dynamic_span") as span:
                span.set_attribute("dynamic_key", "dynamic_value")

            mock_span.set_attribute.assert_called_with("dynamic_key", "dynamic_value")


class TestManualTracingUtilities:
    """Tests for manual tracing utility functions."""

    def test_add_span_attributes(self):
        """Test adding attributes to current span."""
        with patch("app.core.telemetry.trace.get_current_span") as mock_get_span:
            mock_span = MagicMock()
            mock_span.is_recording.return_value = True
            mock_get_span.return_value = mock_span

            add_span_attributes(user_id="123", action="create_order")

            mock_span.set_attribute.assert_any_call("user_id", "123")
            mock_span.set_attribute.assert_any_call("action", "create_order")

    def test_add_span_attributes_no_span(self):
        """Test add_span_attributes when no span is active."""
        with patch("app.core.telemetry.trace.get_current_span") as mock_get_span:
            mock_get_span.return_value = None

            # Should not raise
            add_span_attributes(key="value")

    def test_add_span_attributes_not_recording(self):
        """Test add_span_attributes when span is not recording."""
        with patch("app.core.telemetry.trace.get_current_span") as mock_get_span:
            mock_span = MagicMock()
            mock_span.is_recording.return_value = False
            mock_get_span.return_value = mock_span

            add_span_attributes(key="value")

            mock_span.set_attribute.assert_not_called()

    def test_add_event(self):
        """Test adding event to current span."""
        with patch("app.core.telemetry.trace.get_current_span") as mock_get_span:
            mock_span = MagicMock()
            mock_span.is_recording.return_value = True
            mock_get_span.return_value = mock_span

            add_event("cache_miss", {"cache_key": "user:123"})

            mock_span.add_event.assert_called_once_with("cache_miss", {"cache_key": "user:123"})

    def test_add_event_no_attributes(self):
        """Test adding event without attributes."""
        with patch("app.core.telemetry.trace.get_current_span") as mock_get_span:
            mock_span = MagicMock()
            mock_span.is_recording.return_value = True
            mock_get_span.return_value = mock_span

            add_event("simple_event")

            mock_span.add_event.assert_called_once_with("simple_event", {})

    def test_set_span_error(self):
        """Test setting span error status."""
        with patch("app.core.telemetry.trace.get_current_span") as mock_get_span:
            mock_span = MagicMock()
            mock_span.is_recording.return_value = True
            mock_get_span.return_value = mock_span

            exception = ValueError("Something went wrong")
            set_span_error(exception)

            mock_span.record_exception.assert_called_once_with(exception)
            mock_span.set_status.assert_called_once()
            # Check that status was set with ERROR code
            call_args = mock_span.set_status.call_args[0][0]
            assert call_args.status_code == StatusCode.ERROR


class TestInstrumentation:
    """Tests for automatic instrumentation."""

    def test_instrument_fastapi(self):
        """Test FastAPI instrumentation."""
        with patch("app.core.telemetry.FastAPIInstrumentor") as mock_instrumentor:
            mock_app = MagicMock()

            instrument_fastapi(mock_app)

            mock_instrumentor.instrument_app.assert_called_once_with(
                mock_app,
                excluded_urls="/health,/health/ready",
            )

    def test_instrument_sqlalchemy(self):
        """Test SQLAlchemy instrumentation."""
        with patch("app.core.telemetry.SQLAlchemyInstrumentor") as mock_instrumentor:
            mock_engine = MagicMock()
            mock_engine.sync_engine = MagicMock()

            instrument_sqlalchemy(mock_engine)

            mock_instrumentor.return_value.instrument.assert_called_once()

    def test_instrument_redis(self):
        """Test Redis instrumentation."""
        with patch("app.core.telemetry.RedisInstrumentor") as mock_instrumentor:
            instrument_redis()

            mock_instrumentor.return_value.instrument.assert_called_once()

    def test_instrument_celery(self):
        """Test Celery instrumentation."""
        with patch("app.core.telemetry.CeleryInstrumentor") as mock_instrumentor:
            instrument_celery()

            mock_instrumentor.return_value.instrument.assert_called_once()

    def test_instrument_logging(self):
        """Test logging instrumentation."""
        with patch("app.core.telemetry.LoggingInstrumentor") as mock_instrumentor:
            instrument_logging()

            mock_instrumentor.return_value.instrument.assert_called_once_with(
                set_logging_format=True,
                log_level=20,  # INFO
            )


class TestSetupTelemetry:
    """Tests for complete telemetry setup."""

    def test_setup_telemetry_full(self):
        """Test complete telemetry setup with all instrumentations."""
        with (
            patch("app.core.telemetry.setup_tracer_provider") as mock_setup_provider,
            patch("app.core.telemetry.instrument_fastapi") as mock_fastapi,
            patch("app.core.telemetry.instrument_sqlalchemy") as mock_sqlalchemy,
            patch("app.core.telemetry.instrument_redis") as mock_redis,
            patch("app.core.telemetry.instrument_celery") as mock_celery,
            patch("app.core.telemetry.instrument_logging") as mock_logging,
        ):
            mock_provider = MagicMock()
            mock_setup_provider.return_value = mock_provider

            mock_app = MagicMock()
            mock_engine = MagicMock()

            result = setup_telemetry(app=mock_app, db_engine=mock_engine)

            assert result == mock_provider
            mock_fastapi.assert_called_once_with(mock_app)
            mock_sqlalchemy.assert_called_once_with(mock_engine)
            mock_redis.assert_called_once()
            mock_celery.assert_called_once()
            mock_logging.assert_called_once()

    def test_setup_telemetry_minimal(self):
        """Test telemetry setup without optional components."""
        with (
            patch("app.core.telemetry.setup_tracer_provider") as mock_setup_provider,
            patch("app.core.telemetry.instrument_fastapi") as mock_fastapi,
            patch("app.core.telemetry.instrument_sqlalchemy") as mock_sqlalchemy,
            patch("app.core.telemetry.instrument_redis"),
            patch("app.core.telemetry.instrument_celery"),
            patch("app.core.telemetry.instrument_logging"),
        ):
            mock_provider = MagicMock()
            mock_setup_provider.return_value = mock_provider

            result = setup_telemetry()

            assert result == mock_provider
            mock_fastapi.assert_not_called()
            mock_sqlalchemy.assert_not_called()
