from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.tasks.celery_app import celery_app


@pytest.fixture
def mock_celery_apply(monkeypatch):
    """Mock Celery apply_async for unit tests."""
    mock_result = MagicMock()
    mock_result.id = "test-task-id-123"
    mock = MagicMock(return_value=mock_result)
    monkeypatch.setattr("celery.app.task.Task.apply_async", mock)
    return mock


@pytest.fixture
def eager_celery():
    """Enable Celery eager mode for quick task logic validation."""
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False


@pytest.fixture
def test_db_session():
    """Create a test database session using SQLite."""
    engine = create_engine("sqlite:///:memory:")
    TestSession = sessionmaker(bind=engine)

    from app.db.base import Base

    Base.metadata.create_all(engine)

    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def mock_sync_session(test_db_session):
    """Mock the get_sync_session to return test session."""
    with patch("app.tasks.db.get_sync_session", return_value=iter([test_db_session])):
        yield test_db_session
