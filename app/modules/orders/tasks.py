from app.modules.orders.models import Order, OrderStatus
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_session


@celery_app.task(bind=True, max_retries=3, retry_backoff=True)
def cancel_timeout(self, order_id: int):
    """Cancel order if still PENDING after timeout."""
    session = next(get_sync_session())
    try:
        order = session.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"skipped": True, "reason": "order not found"}

        # Idempotent: only cancel if still PENDING
        if order.status != OrderStatus.PENDING.value:
            return {"skipped": True, "reason": f"status is {order.status}"}

        order.status = OrderStatus.CANCELLED.value
        session.commit()
        return {"cancelled": True, "order_id": order_id}
    except Exception as exc:
        session.rollback()
        raise self.retry(exc=exc)
    finally:
        session.close()
