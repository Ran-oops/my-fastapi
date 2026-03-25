from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.tasks.repository import get_task_by_id, get_tasks, update_task_status
from app.tasks.models import TaskStatus


def get_task(session: Session, task_id: int):
    return get_task_by_id(session, task_id)


def list_tasks(
    session: Session, status: str | None = None, task_name: str | None = None, page: int = 1, page_size: int = 10
):
    skip = (page - 1) * page_size
    return get_tasks(session, status=status, task_name=task_name, skip=skip, limit=page_size)


def retry_task(session: Session, task_id: int):
    from app.tasks.dispatcher import dispatch_by_task_name

    task_record = get_task_by_id(session, task_id)
    if not task_record:
        raise NotFoundException("Task not found")
    if task_record.status not in (TaskStatus.FAILED.value, TaskStatus.DEAD.value):
        raise ValidationException(f"Cannot retry task with status {task_record.status}")

    update_task_status(session, task_id, TaskStatus.PENDING.value)
    session.commit()
    dispatch_by_task_name(task_record.task_name, task_record.params or {})
    return task_record


def cancel_task(session: Session, task_id: int):
    from app.tasks.celery_app import celery_app

    task_record = get_task_by_id(session, task_id)
    if not task_record:
        raise NotFoundException("Task not found")
    if task_record.status != TaskStatus.PENDING.value:
        raise ValidationException(f"Cannot cancel task with status {task_record.status}")

    if task_record.celery_task_id:
        celery_app.control.revoke(task_record.celery_task_id, terminate=True)

    update_task_status(session, task_id, TaskStatus.CANCELLED.value)
    session.commit()
    return task_record
