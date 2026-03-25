from app.tasks.db import get_sync_session
from app.tasks.repository import create_task_record, update_celery_task_id, update_task_status, find_pending_task


def dispatch(task, *args, **kwargs):
    """Create TaskRecord + dispatch Celery task atomically."""
    session = next(get_sync_session())
    record = None
    try:
        # Extract Celery-specific kwargs
        countdown = kwargs.pop("countdown", None)
        eta = kwargs.pop("eta", None)

        params = {"args": list(args), "kwargs": kwargs}

        # Deduplication: check for existing pending task
        existing = find_pending_task(session, task.name, params)
        if existing:
            return existing

        record = create_task_record(session, task.name, params=params)

        # Dispatch to Celery
        apply_kwargs = {}
        if countdown is not None:
            apply_kwargs["countdown"] = countdown
        if eta is not None:
            apply_kwargs["eta"] = eta

        result = task.apply_async(args=args, kwargs=kwargs, **apply_kwargs)
        update_celery_task_id(session, record.id, result.id)
        session.commit()
        return record
    except Exception as e:
        session.rollback()
        # Update original record as FAILED if it was created
        if record is not None:
            try:
                update_task_status(session, record.id, "FAILED", error=f"Dispatch failed: {e}")
                session.commit()
            except Exception:
                session.rollback()
        raise
    finally:
        session.close()


def dispatch_by_task_name(task_name: str, params: dict):
    """Dispatch a task by its registered name (for retry/revive)."""
    from app.tasks.celery_app import celery_app

    task = celery_app.tasks.get(task_name)
    if not task:
        raise ValueError(f"Task {task_name} not registered")

    args = params.get("args", [])
    kwargs = params.get("kwargs", {})
    dispatch(task, *args, **kwargs)
