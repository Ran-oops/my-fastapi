import csv
import json
import tempfile
from datetime import datetime

from app.modules.orders.models import Order
from app.modules.products.models import Product
from app.modules.audit.models import AuditLog
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_session


def _write_excel(data: list[dict], headers: list[str], file_path: str) -> None:
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl is required for Excel export. Install with: pip install openpyxl")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in data:
        ws.append([row.get(h) for h in headers])
    wb.save(file_path)


@celery_app.task(bind=True, max_retries=2, retry_backoff=True)
def export_order_data(self, filters: dict, format: str = "csv"):
    """Export order data to CSV/JSON/Excel file."""
    session = next(get_sync_session())
    try:
        query = session.query(Order).order_by(Order.id.desc())

        if filters.get("status"):
            query = query.filter(Order.status == filters["status"])
        if filters.get("user_id"):
            query = query.filter(Order.user_id == filters["user_id"])
        if filters.get("date_from"):
            query = query.filter(Order.created_at >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(Order.created_at <= filters["date_to"])

        limit = filters.get("limit", 1000)
        orders = query.limit(limit).all()

        if format == "excel":
            data = [
                {
                    "id": order.id,
                    "user_id": order.user_id,
                    "status": order.status,
                    "total_amount": str(order.total_amount),
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                }
                for order in orders
            ]
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".xlsx", delete=False) as f:
                _write_excel(data, ["id", "user_id", "status", "total_amount", "created_at"], f.name)
                return {"file_path": f.name, "count": len(orders)}

        with tempfile.NamedTemporaryFile(mode="w", suffix=f".{format}", delete=False, newline="") as f:
            if format == "csv":
                writer = csv.writer(f)
                writer.writerow(["id", "user_id", "status", "total_amount", "created_at"])
                for order in orders:
                    writer.writerow([order.id, order.user_id, order.status, order.total_amount, order.created_at])
            elif format == "json":
                data = [
                    {
                        "id": order.id,
                        "user_id": order.user_id,
                        "status": order.status,
                        "total_amount": str(order.total_amount),
                        "created_at": order.created_at.isoformat() if order.created_at else None,
                    }
                    for order in orders
                ]
                json.dump(data, f, indent=2)

            return {"file_path": f.name, "count": len(orders)}
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=2, retry_backoff=True)
def export_product_data(self, filters: dict, format: str = "csv"):
    """Export product data to CSV/JSON/Excel file."""
    session = next(get_sync_session())
    try:
        query = session.query(Product).order_by(Product.id.desc())

        if filters.get("category"):
            query = query.filter(Product.category == filters["category"])
        if filters.get("is_active") is not None:
            query = query.filter(Product.is_active == filters["is_active"])

        limit = filters.get("limit", 1000)
        products = query.limit(limit).all()

        if format == "excel":
            data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "price": str(p.price),
                    "category": p.category,
                    "is_active": p.is_active,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in products
            ]
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".xlsx", delete=False) as f:
                _write_excel(data, ["id", "name", "sku", "price", "category", "is_active", "created_at"], f.name)
                return {"file_path": f.name, "count": len(products)}

        with tempfile.NamedTemporaryFile(mode="w", suffix=f".{format}", delete=False, newline="") as f:
            if format == "csv":
                writer = csv.writer(f)
                writer.writerow(["id", "name", "sku", "price", "category", "is_active", "created_at"])
                for product in products:
                    writer.writerow(
                        [
                            product.id,
                            product.name,
                            product.sku,
                            product.price,
                            product.category,
                            product.is_active,
                            product.created_at,
                        ]
                    )
            elif format == "json":
                data = [
                    {
                        "id": p.id,
                        "name": p.name,
                        "sku": p.sku,
                        "price": str(p.price),
                        "category": p.category,
                        "is_active": p.is_active,
                        "created_at": p.created_at.isoformat() if p.created_at else None,
                    }
                    for p in products
                ]
                json.dump(data, f, indent=2)

            return {"file_path": f.name, "count": len(products)}
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=2, retry_backoff=True)
def export_audit_logs(self, filters: dict, format: str = "csv"):
    """Export audit logs to CSV/JSON/Excel file."""
    session = next(get_sync_session())
    try:
        query = session.query(AuditLog).order_by(AuditLog.id.desc())

        if filters.get("user_id"):
            query = query.filter(AuditLog.user_id == filters["user_id"])
        if filters.get("action"):
            query = query.filter(AuditLog.action == filters["action"])
        if filters.get("resource_type"):
            query = query.filter(AuditLog.resource_type == filters["resource_type"])
        if filters.get("date_from"):
            query = query.filter(AuditLog.created_at >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(AuditLog.created_at <= filters["date_to"])

        limit = filters.get("limit", 1000)
        logs = query.limit(limit).all()

        if format == "excel":
            data = [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ]
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".xlsx", delete=False) as f:
                _write_excel(
                    data,
                    ["id", "user_id", "action", "resource_type", "resource_id", "ip_address", "created_at"],
                    f.name,
                )
                return {"file_path": f.name, "count": len(logs)}

        with tempfile.NamedTemporaryFile(mode="w", suffix=f".{format}", delete=False, newline="") as f:
            if format == "csv":
                writer = csv.writer(f)
                writer.writerow(["id", "user_id", "action", "resource_type", "resource_id", "ip_address", "created_at"])
                for log in logs:
                    writer.writerow(
                        [
                            log.id,
                            log.user_id,
                            log.action,
                            log.resource_type,
                            log.resource_id,
                            log.ip_address,
                            log.created_at,
                        ]
                    )
            elif format == "json":
                data = [
                    {
                        "id": log.id,
                        "user_id": log.user_id,
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "ip_address": log.ip_address,
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                    }
                    for log in logs
                ]
                json.dump(data, f, indent=2)

            return {"file_path": f.name, "count": len(logs)}
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        session.close()
