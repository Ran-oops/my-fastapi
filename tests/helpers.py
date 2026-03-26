import uuid
from decimal import Decimal

from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from app.modules.products.schemas import ProductCreate
from app.modules.audit.schemas import AuditLogCreate


def make_product_data(**overrides):
    """Create product data with optional overrides."""
    base = {
        "name": f"Test Product {uuid.uuid4().hex[:8]}",
        "sku": f"SKU-{uuid.uuid4().hex[:8]}",
        "price": Decimal("99.99"),
        "category": "test",
    }
    base.update(overrides)
    return ProductCreate(**base)


def make_order_item_data(product_id, **overrides):
    """Create order item data with optional overrides."""
    base = {
        "product_id": product_id,
        "quantity": 1,
        "unit_price": Decimal("10.00"),
    }
    base.update(overrides)
    return OrderItemCreate(**base)


def make_order_data(user_id, product_id, **overrides):
    """Create order data with optional overrides."""
    base = {
        "user_id": user_id,
        "items": [make_order_item_data(product_id)],
    }
    base.update(overrides)
    return OrderCreate(**base)


def make_audit_log_data(**overrides):
    """Create audit log data with optional overrides."""
    base = {
        "user_id": 1,
        "action": "create",
        "resource_type": "product",
        "resource_id": 1,
    }
    base.update(overrides)
    return AuditLogCreate(**base)
