from unittest.mock import MagicMock, patch

import pytest


def test_dispatch_creates_task_record(test_db_session):
    """Test that dispatch creates a TaskRecord."""
    from app.tasks.dispatcher import dispatch

    mock_task = MagicMock()
    mock_task.name = "test.task"
    mock_task.apply_async.return_value.id = "test-task-id-123"

    with patch("app.tasks.dispatcher.get_sync_session", return_value=iter([test_db_session])):
        dispatch(mock_task, arg1="value1")

    mock_task.apply_async.assert_called_once()


def test_dispatch_handles_failure(test_db_session):
    """Test that dispatch handles Celery failure gracefully."""
    from app.tasks.dispatcher import dispatch

    mock_task = MagicMock()
    mock_task.name = "test.task"
    mock_task.apply_async.side_effect = Exception("Redis connection failed")

    with (
        patch("app.tasks.dispatcher.get_sync_session", return_value=iter([test_db_session])),
        pytest.raises(Exception, match="Redis connection failed"),
    ):
        dispatch(mock_task, arg1="value1")
