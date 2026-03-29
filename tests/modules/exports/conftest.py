from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_export_dispatch():
    """Mock the Celery dispatch for export endpoints."""
    with patch("app.modules.exports.router.dispatch") as mock_dispatch:
        mock_result = MagicMock()
        mock_result.id = "test-task-id"
        mock_dispatch.return_value = mock_result
        yield mock_dispatch


@pytest.fixture
def mock_celery_success():
    """Mock Celery AsyncResult in SUCCESS state."""
    with patch("app.modules.exports.router.celery_app") as mock_celery:
        mock_async_result = MagicMock()
        mock_async_result.state = "SUCCESS"
        mock_async_result.result = {"file_path": "/tmp/test.csv", "count": 10}
        mock_celery.AsyncResult.return_value = mock_async_result
        yield mock_celery


@pytest.fixture
def mock_celery_pending():
    """Mock Celery AsyncResult in PENDING state."""
    with patch("app.modules.exports.router.celery_app") as mock_celery:
        mock_async_result = MagicMock()
        mock_async_result.state = "PENDING"
        mock_celery.AsyncResult.return_value = mock_async_result
        yield mock_celery
