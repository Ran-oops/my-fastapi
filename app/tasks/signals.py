from celery.signals import task_failure, task_postrun, task_prerun

from app.tasks.db import get_sync_session
from app.tasks.repository import update_task_status_by_celery_id


@task_prerun.connect
def task_started(_sender, task_id, **_kwargs):
    session = next(get_sync_session())
    try:
        update_task_status_by_celery_id(session, task_id, "RUNNING")
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@task_postrun.connect
def task_completed(_sender, task_id, _retval, state, **_kwargs):
    session = next(get_sync_session())
    try:
        status = "SUCCESS" if state == "SUCCESS" else "FAILED"
        update_task_status_by_celery_id(session, task_id, status)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@task_failure.connect
def task_failed(_sender, task_id, exception, **_kwargs):
    session = next(get_sync_session())
    try:
        update_task_status_by_celery_id(session, task_id, "FAILED", error=str(exception))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
