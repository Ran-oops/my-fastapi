from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.tasks.models import TaskRecord, TaskStatus


def create_task_record(session: Session, task_name: str, params: dict | None = None) -> TaskRecord:
    record = TaskRecord(task_name=task_name, params=params, status=TaskStatus.PENDING.value)
    session.add(record)
    session.flush()
    return record


def update_celery_task_id(session: Session, record_id: int, celery_task_id: str) -> None:
    record = session.get(TaskRecord, record_id)
    if record:
        record.celery_task_id = celery_task_id
        session.flush()


def _apply_status_update(record: TaskRecord, status: str, error: str | None = None) -> None:
    record.status = status
    if error:
        record.error = error
    if status in (TaskStatus.SUCCESS.value, TaskStatus.FAILED.value, TaskStatus.DEAD.value):
        record.completed_at = datetime.now(timezone.utc)


def update_task_status(session: Session, record_id: int, status: str, error: str | None = None) -> None:
    record = session.get(TaskRecord, record_id)
    if record:
        _apply_status_update(record, status, error)
        session.flush()


def update_task_status_by_celery_id(
    session: Session, celery_task_id: str, status: str, error: str | None = None
) -> None:
    record = session.query(TaskRecord).filter(TaskRecord.celery_task_id == celery_task_id).first()
    if record:
        _apply_status_update(record, status, error)
        session.flush()


def find_pending_task(session: Session, task_name: str, params: dict | None = None) -> TaskRecord | None:
    query = session.query(TaskRecord).filter(
        TaskRecord.task_name == task_name,
        TaskRecord.status == TaskStatus.PENDING.value,
    )
    if params:
        query = query.filter(TaskRecord.params == params)
    return query.first()


def get_task_by_id(session: Session, task_id: int) -> TaskRecord | None:
    return session.get(TaskRecord, task_id)


def get_tasks(
    session: Session, status: str | None = None, task_name: str | None = None, skip: int = 0, limit: int = 10
) -> tuple[list[TaskRecord], int]:
    query = session.query(TaskRecord)
    if status:
        query = query.filter(TaskRecord.status == status)
    if task_name:
        query = query.filter(TaskRecord.task_name == task_name)
    total = query.count()
    records = query.order_by(TaskRecord.created_at.desc()).offset(skip).limit(limit).all()
    return list(records), total
