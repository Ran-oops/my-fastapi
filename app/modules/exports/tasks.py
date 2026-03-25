import csv
import tempfile

from app.modules.orders.models import Order
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_session


@celery_app.task(bind=True, max_retries=2, retry_backoff=True)
def export_order_data(self, _filters: dict, format: str = "csv"):
    """Export order data to CSV/Excel file."""
    session = next(get_sync_session())
    try:
        orders = session.query(Order).order_by(Order.id.desc()).limit(1000).all()

        with tempfile.NamedTemporaryFile(mode="w", suffix=f".{format}", delete=False, newline="") as f:
            if format == "csv":
                writer = csv.writer(f)
                writer.writerow(["id", "user_id", "status", "total_amount", "created_at"])
                for order in orders:
                    writer.writerow([order.id, order.user_id, order.status, order.total_amount, order.created_at])

        return {"file_path": f.name, "count": len(orders)}
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        session.close()
