from app.modules.audit.models import AuditLog
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_session


@celery_app.task
def write_audit_log(user_id: int, action: str, resource_type: str, resource_id: int, **kwargs):
    """Write audit log entry asynchronously."""
    session = next(get_sync_session())
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=kwargs.get("old_value"),
            new_value=kwargs.get("new_value"),
            ip_address=kwargs.get("ip_address"),
        )
        session.add(audit_log)
        session.commit()
        return {"logged": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
