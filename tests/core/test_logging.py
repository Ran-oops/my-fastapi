"""Tests for structured logging configuration using structlog.

This module tests:
- Structured logging configuration
- Log processors and formatters
- JSON format output in production
- Console format output in development
- Trace ID injection
- Different log levels
"""

import json
import logging
from contextvars import ContextVar
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
import structlog

from app.core.logging import (
    add_logger_name,
    add_trace_id,
    configure_logging,
    get_logger,
    get_stdlib_processors,
    get_structlog_processors,
    lowercase_log_level,
    rename_message_to_event,
    set_trace_id,
    get_trace_id,
)


class TestTraceIdProcessors:
    """Tests for trace ID processor functions."""

    def test_add_trace_id_with_value(self):
        """Test that trace_id is added when available in context."""
        mock_logger = MagicMock()
        mock_logger.name = "test_logger"
        event_dict = {"event": "test_message"}

        # Create a context var with a value
        trace_id_var = ContextVar("trace_id", default=None)
        token = trace_id_var.set("abc-123-trace")

        # Patch the ContextVar creation in add_trace_id
        with patch("app.core.logging.ContextVar") as mock_ctx:
            mock_ctx.return_value = trace_id_var
            result = add_trace_id(mock_logger, "info", event_dict)

        assert result["trace_id"] == "abc-123-trace"
        trace_id_var.reset(token)

    def test_add_trace_id_without_value(self):
        """Test that trace_id is not added when not available."""
        mock_logger = MagicMock()
        mock_logger.name = "test_logger"
        event_dict = {"event": "test_message"}

        with patch("app.core.logging.ContextVar") as mock_ctx:
            mock_ctx_var = MagicMock()
            mock_ctx_var.get.return_value = None
            mock_ctx.return_value = mock_ctx_var
            result = add_trace_id(mock_logger, "info", event_dict)

        assert "trace_id" not in result

    def test_add_logger_name(self):
        """Test that logger name is added to event dict."""
        mock_logger = MagicMock()
        mock_logger.name = "my.module.logger"
        event_dict = {"event": "test"}

        result = add_logger_name(mock_logger, "info", event_dict)

        assert result["logger"] == "my.module.logger"

    def test_add_logger_name_existing(self):
        """Test that existing logger name is preserved."""
        mock_logger = MagicMock()
        mock_logger.name = "new.logger"
        event_dict = {"event": "test", "logger": "existing.logger"}

        result = add_logger_name(mock_logger, "info", event_dict)

        assert result["logger"] == "existing.logger"


class TestLogFormatProcessors:
    """Tests for log format processors."""

    def test_rename_message_to_event(self):
        """Test that 'event' is renamed to 'message'."""
        mock_logger = MagicMock()
        event_dict = {"event": "test message", "level": "info"}

        result = rename_message_to_event(mock_logger, "info", event_dict)

        assert "event" not in result
        assert result["message"] == "test message"
        assert result["level"] == "info"

    def test_rename_message_to_event_no_event(self):
        """Test that dict without 'event' key is unchanged."""
        mock_logger = MagicMock()
        event_dict = {"level": "info", "custom": "value"}

        result = rename_message_to_event(mock_logger, "info", event_dict)

        assert "event" not in result
        assert result["level"] == "info"
        assert result["custom"] == "value"

    def test_lowercase_log_level(self):
        """Test that log level is converted to lowercase."""
        mock_logger = MagicMock()
        event_dict = {"level": "INFO"}

        result = lowercase_log_level(mock_logger, "info", event_dict)

        assert result["level"] == "info"

    def test_lowercase_log_level_already_lowercase(self):
        """Test that lowercase level remains unchanged."""
        mock_logger = MagicMock()
        event_dict = {"level": "error"}

        result = lowercase_log_level(mock_logger, "error", event_dict)

        assert result["level"] == "error"


class TestStructlogProcessors:
    """Tests for structlog processors configuration."""

    def test_get_structlog_processors_development(self):
        """Test processors in development environment."""
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.APP_ENV = "development"
            processors = get_structlog_processors()

        # Check that common processors are present
        processor_names = [p.__name__ if hasattr(p, "__name__") else str(p) for p in processors]

        # Should have ConsoleRenderer in development
        assert any("ConsoleRenderer" in str(p) for p in processors)
        # Should NOT have JSONRenderer in development
        assert not any("JSONRenderer" in str(p) for p in processors)

    def test_get_structlog_processors_production(self):
        """Test processors in production environment."""
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.APP_ENV = "production"
            processors = get_structlog_processors()

        # Should have JSONRenderer in production
        assert any("JSONRenderer" in str(p) for p in processors)
        # Should NOT have ConsoleRenderer in production
        assert not any("ConsoleRenderer" in str(p) for p in processors)
        # Should have custom processors
        assert add_trace_id in processors
        assert add_logger_name in processors

    def test_get_stdlib_processors(self):
        """Test stdlib logging processors."""
        processors = get_stdlib_processors()

        # Check expected processors are present
        assert len(processors) > 0
        assert any("filter_by_level" in str(p) for p in processors)
        assert any("add_logger_name" in str(p) for p in processors)
        assert any("add_log_level" in str(p) for p in processors)


class TestLoggerConfiguration:
    """Tests for logging configuration."""

    def test_configure_logging_sets_level(self):
        """Test that logging configuration sets the correct level."""
        with (
            patch("app.core.logging.logging.config.dictConfig") as mock_dict_config,
            patch("app.core.logging.structlog.configure") as mock_struct_config,
            patch("app.core.logging.settings") as mock_settings,
        ):
            mock_settings.LOG_LEVEL = "DEBUG"
            mock_settings.APP_ENV = "development"

            configure_logging()

        # Verify dictConfig was called
        assert mock_dict_config.called
        # Verify structlog.configure was called
        assert mock_struct_config.called

    def test_configure_logging_production_handlers(self):
        """Test that production uses JSON handlers."""
        with (
            patch("app.core.logging.logging.config.dictConfig") as mock_dict_config,
            patch("app.core.logging.structlog.configure"),
            patch("app.core.logging.settings") as mock_settings,
        ):
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.APP_ENV = "production"

            configure_logging()

        # Get the config passed to dictConfig
        config = mock_dict_config.call_args[0][0]

        # Root handler should be json_console in production
        assert "json_console" in config["root"]["handlers"]
        assert "console" not in config["root"]["handlers"]

    def test_configure_logging_development_handlers(self):
        """Test that development uses standard console handlers."""
        with (
            patch("app.core.logging.logging.config.dictConfig") as mock_dict_config,
            patch("app.core.logging.structlog.configure"),
            patch("app.core.logging.settings") as mock_settings,
        ):
            mock_settings.LOG_LEVEL = "DEBUG"
            mock_settings.APP_ENV = "development"

            configure_logging()

        # Get the config passed to dictConfig
        config = mock_dict_config.call_args[0][0]

        # Root handler should be console in development
        assert "console" in config["root"]["handlers"]
        assert "json_console" not in config["root"]["handlers"]


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_with_name(self):
        """Test getting logger with explicit name."""
        with patch("app.core.logging.structlog.get_logger") as mock_get:
            mock_logger = MagicMock()
            mock_get.return_value = mock_logger

            result = get_logger("my.module")

            mock_get.assert_called_once_with("my.module")
            assert result == mock_logger

    def test_get_logger_without_name(self):
        """Test getting logger without name (defaults to None)."""
        with patch("app.core.logging.structlog.get_logger") as mock_get:
            mock_logger = MagicMock()
            mock_get.return_value = mock_logger

            result = get_logger()

            mock_get.assert_called_once_with(None)
            assert result == mock_logger


class TestTraceIdFunctions:
    """Tests for trace ID getter and setter functions."""

    def test_set_trace_id_sets_global(self):
        """Test that set_trace_id sets the global trace_id variable."""
        with patch("app.core.logging.ContextVar") as mock_ctx:
            mock_var = MagicMock()
            mock_ctx.return_value = mock_var

            set_trace_id("trace-123")

            mock_var.set.assert_called_once_with("trace-123")

    def test_set_trace_id_with_none(self):
        """Test that set_trace_id clears trace_id when None."""
        with patch("app.core.logging.ContextVar") as mock_ctx:
            mock_var = MagicMock()
            mock_ctx.return_value = mock_var

            set_trace_id(None)

            mock_var.set.assert_called_once_with(None)

    def test_get_trace_id_returns_global(self):
        """Test that get_trace_id returns the global trace_id."""
        with patch("app.core.logging._trace_id", "stored-trace-123"):
            result = get_trace_id()
            assert result == "stored-trace-123"


class TestLogLevels:
    """Tests for different log levels."""

    @pytest.mark.asyncio
    async def test_logger_debug_level(self):
        """Test that logger supports DEBUG level."""
        with patch("app.core.logging.structlog.get_logger") as mock_get:
            mock_logger = MagicMock()
            mock_get.return_value = mock_logger

            logger = get_logger("test")
            logger.debug("debug message")

            mock_logger.debug.assert_called_once_with("debug message")

    @pytest.mark.asyncio
    async def test_logger_info_level(self):
        """Test that logger supports INFO level."""
        with patch("app.core.logging.structlog.get_logger") as mock_get:
            mock_logger = MagicMock()
            mock_get.return_value = mock_logger

            logger = get_logger("test")
            logger.info("info message", extra_key="value")

            mock_logger.info.assert_called_once_with("info message", extra_key="value")

    @pytest.mark.asyncio
    async def test_logger_warning_level(self):
        """Test that logger supports WARNING level."""
        with patch("app.core.logging.structlog.get_logger") as mock_get:
            mock_logger = MagicMock()
            mock_get.return_value = mock_logger

            logger = get_logger("test")
            logger.warning("warning message")

            mock_logger.warning.assert_called_once_with("warning message")

    @pytest.mark.asyncio
    async def test_logger_error_level(self):
        """Test that logger supports ERROR level."""
        with patch("app.core.logging.structlog.get_logger") as mock_get:
            mock_logger = MagicMock()
            mock_get.return_value = mock_logger

            logger = get_logger("test")
            logger.error("error message", exc_info=True)

            mock_logger.error.assert_called_once_with("error message", exc_info=True)

    @pytest.mark.asyncio
    async def test_logger_critical_level(self):
        """Test that logger supports CRITICAL level."""
        with patch("app.core.logging.structlog.get_logger") as mock_get:
            mock_logger = MagicMock()
            mock_get.return_value = mock_logger

            logger = get_logger("test")
            logger.critical("critical message")

            mock_logger.critical.assert_called_once_with("critical message")


class TestJSONOutput:
    """Tests for JSON formatted log output."""

    def test_json_output_contains_required_fields(self):
        """Test that JSON output contains required structured logging fields."""
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.APP_ENV = "production"
            processors = get_structlog_processors()

            # Check JSONRenderer is included
            assert any(isinstance(p, structlog.processors.JSONRenderer) for p in processors)

    def test_json_output_formatting(self):
        """Test JSON formatting of log events."""
        event_dict = {
            "timestamp": "2024-01-15T10:30:00",
            "level": "info",
            "message": "Test message",
            "trace_id": "abc-123",
        }

        renderer = structlog.processors.JSONRenderer()
        output = renderer(None, None, event_dict)

        # Parse the JSON output
        parsed = json.loads(output)
        assert parsed["level"] == "info"
        assert parsed["message"] == "Test message"
        assert parsed["trace_id"] == "abc-123"


class TestConsoleOutput:
    """Tests for console formatted log output."""

    def test_console_output_in_development(self):
        """Test that console output is configured in development."""
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.APP_ENV = "development"
            processors = get_structlog_processors()

            # Check ConsoleRenderer is included
            assert any(isinstance(p, structlog.dev.ConsoleRenderer) for p in processors)

    def test_console_renderer_configuration(self):
        """Test console renderer configuration."""
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.APP_ENV = "development"
            processors = get_structlog_processors()

            # Find ConsoleRenderer
            console_renderer = None
            for p in processors:
                if isinstance(p, structlog.dev.ConsoleRenderer):
                    console_renderer = p
                    break

            assert console_renderer is not None
