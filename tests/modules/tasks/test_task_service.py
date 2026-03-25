from app.tasks.models import TaskStatus


def test_create_task_record(test_db_session):
    """Test creating a task record."""
    from app.tasks.repository import create_task_record

    record = create_task_record(test_db_session, "test.task", params={"key": "value"})
    test_db_session.commit()
    assert record.id is not None
    assert record.task_name == "test.task"
    assert record.status == TaskStatus.PENDING.value


def test_update_task_status(test_db_session):
    """Test updating task status."""
    from app.tasks.repository import create_task_record, get_task_by_id, update_task_status

    record = create_task_record(test_db_session, "test.task")
    test_db_session.commit()

    update_task_status(test_db_session, record.id, TaskStatus.SUCCESS.value)
    test_db_session.commit()

    updated = get_task_by_id(test_db_session, record.id)
    assert updated.status == TaskStatus.SUCCESS.value
    assert updated.completed_at is not None


def test_find_pending_task(test_db_session):
    """Test finding pending tasks."""
    from app.tasks.repository import create_task_record, find_pending_task

    params = {"order_id": 42}
    record = create_task_record(test_db_session, "orders.cancel_timeout", params=params)
    test_db_session.commit()

    found = find_pending_task(test_db_session, "orders.cancel_timeout", params)
    assert found is not None
    assert found.id == record.id
