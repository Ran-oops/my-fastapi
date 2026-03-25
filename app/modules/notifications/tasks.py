from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, retry_backoff=True)
def send_notification(self, user_id: int, template: str, context: dict):
    """Send notification to user asynchronously."""
    try:
        from app.modules.notifications.service import deliver_notification

        result = deliver_notification(user_id, template, context)
        return result
    except Exception as exc:
        raise self.retry(exc=exc)
