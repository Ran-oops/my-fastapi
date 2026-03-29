import uuid
from decimal import Decimal

from app.modules.audit.schemas import AuditLogCreate
from app.modules.notifications.models import Notification, NotificationTemplate
from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from app.modules.products.schemas import ProductCreate
from tests.conftest import TEST_PASSWORD


def unique_id():
    """Generate a short unique hex string for test data."""
    return uuid.uuid4().hex[:8]


def make_product_data(**overrides):
    """Create product data with optional overrides."""
    base = {
        "name": f"Test Product {unique_id()}",
        "sku": f"SKU-{unique_id()}",
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


def make_notification(user_id, **overrides):
    """Build a Notification ORM instance (not yet persisted)."""
    defaults = {
        "user_id": user_id,
        "template_name": f"test.notify.{unique_id()}",
        "channel": "in_app",
        "status": "sent",
        "subject": "Test Subject",
        "body": "Test notification body",
        "is_read": False,
    }
    defaults.update(overrides)
    return Notification(**defaults)


def make_template(**overrides):
    """Build a NotificationTemplate ORM instance (not yet persisted)."""
    defaults = {
        "name": f"test.event.{unique_id()}",
        "channel": "in_app",
        "subject": "Test Subject",
        "body": "Hello {{user_id}}, message: {{message}}",
        "is_active": True,
    }
    defaults.update(overrides)
    return NotificationTemplate(**defaults)


async def register_and_login(client, password=TEST_PASSWORD):
    """Register a user and return (user_data, token, headers).

    Generates unique email/username automatically.
    """
    uid = unique_id()
    user_data = {
        "email": f"user_{uid}@example.com",
        "username": f"user_{uid}",
        "password": password,
    }
    await client.post("/api/v1/auth/register", json=user_data)
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": user_data["username"], "password": password},
    )
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return user_data, token, headers
