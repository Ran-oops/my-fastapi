# Test Code Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Full structural rewrite of all test files to eliminate duplication, improve patterns, and standardize conventions.

**Architecture:** Move shared fixtures to root conftest, add factory helpers, use parametrize for repeated patterns, fix import practices, enforce consistent assertion style across all 13 test files.

**Tech Stack:** pytest, pytest-asyncio, httpx, SQLAlchemy async

**Spec:** `docs/superpowers/specs/2026-03-26-test-code-refactoring-design.md`

---

## File Structure

```text
tests/
├── conftest.py                    # Modify: add superuser_headers, user_headers
├── helpers.py                     # Create: factory functions
├── modules/
│   ├── orders/
│   │   ├── conftest.py            # Rewrite: add patch_dispatch, fresh_order
│   │   ├── test_order_service.py  # Rewrite: parametrize, fixture usage
│   │   └── test_order_api.py      # Rewrite: patch_dispatch fixture
│   ├── products/
│   │   ├── conftest.py            # Modify: remove duplicated fixtures
│   │   ├── test_product_service.py # Modify: fix imports, helpers
│   │   └── test_product_api.py    # Modify: fix assertions
│   ├── audit/
│   │   ├── conftest.py            # Modify: remove duplicated fixtures
│   │   ├── test_audit_service.py  # Modify: add type hints
│   │   └── test_audit_api.py      # Modify: fix assertions
│   └── roles/
│       ├── test_role_service.py       # Modify: move import uuid to top
│       └── test_permission_service.py # Modify: move import uuid to top
```

---

## Task 1: Root conftest.py + helpers.py

**Files:**

- Modify: `tests/conftest.py`
- Create: `tests/helpers.py`

- [ ] **Step 1: Add shared fixtures to tests/conftest.py**

Append to the end of `tests/conftest.py`:

```python
@pytest_asyncio.fixture
async def superuser_headers(superuser_token):
    """Headers for admin API calls."""
    return {"Authorization": f"Bearer {superuser_token}"}


@pytest_asyncio.fixture
async def user_headers(user_token):
    """Headers for regular user API calls."""
    return {"Authorization": f"Bearer {user_token}"}
```

- [ ] **Step 2: Create tests/helpers.py**

```python
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
```

- [ ] **Step 3: Run tests to verify nothing breaks**
Run: `uv run pytest tests -v --tb=short`
Expected: All existing tests PASS (new fixtures don't conflict)

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/helpers.py
git commit -m "test: add shared fixtures and factory helpers"
```

---

## Task 2: Orders conftest.py Rewrite

**Files:**

- Rewrite: `tests/modules/orders/conftest.py`

- [ ] **Step 1: Rewrite orders conftest.py**

```python
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest_asyncio

from app.modules.orders import service as order_service
from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from app.modules.products import service as product_service
from app.modules.products.schemas import ProductCreate


@pytest_asyncio.fixture
async def test_product_for_order(session):
    """Create a product for order tests."""
    product_in = ProductCreate(
        name="Test Product for Order",
        sku=f"TEST-ORDER-{uuid.uuid4().hex[:8]}",
        price=Decimal("99.99"),
        category="test",
    )
    return await product_service.create_product(session, product_in)


@pytest_asyncio.fixture
async def test_order(session, test_user, test_product_for_order):
    """Create a test order with items."""
    with patch("app.modules.orders.service.dispatch"):
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(
                    product_id=test_product_for_order.id,
                    quantity=2,
                    unit_price=test_product_for_order.price,
                )
            ],
        )
        return await order_service.create_order(session, order_in)


@pytest_asyncio.fixture
def patch_dispatch():
    """Mock the Celery dispatch to avoid real task execution."""
    with patch("app.modules.orders.service.dispatch"):
        yield


@pytest_asyncio.fixture
async def fresh_order(session, test_user, test_product_for_order, patch_dispatch):
    """Create a fresh PENDING order for each test that needs one."""
    order_in = OrderCreate(
        user_id=test_user.id,
        items=[
            OrderItemCreate(
                product_id=test_product_for_order.id,
                quantity=1,
                unit_price=Decimal("10.00"),
            )
        ],
    )
    return await order_service.create_order(session, order_in)
```

- [ ] **Step 2: Remove duplicated fixtures** (superuser_headers, user_headers already removed)
- [ ] **Step 3: Run orders tests**
Run: `uv run pytest tests/modules/orders -v --tb=short`
Expected: All existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/modules/orders/conftest.py
git commit -m "test(orders): add patch_dispatch and fresh_order fixtures"
```

---

## Task 3: Orders Service Tests Rewrite

**Files:**

- Rewrite: `tests/modules/orders/test_order_service.py`

- [ ] **Step 1: Rewrite the file**

```python
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.orders import service as order_service
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderItemCreate, OrderUpdate


@pytest.mark.asyncio
class TestOrderServiceCreate:
    async def test_create_order_success(self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch):
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(product_id=test_product_for_order.id, quantity=2, unit_price=Decimal("99.99")),
                OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("50.00")),
            ],
        )
        order = await order_service.create_order(session, order_in)
        assert order.id is not None
        assert order.user_id == test_user.id
        assert order.status == OrderStatus.PENDING.value
        assert order.total_amount == Decimal("249.98")
        result = await session.execute(select(Order).options(selectinload(Order.items)).where(Order.id == order.id))
        assert len(result.scalar_one().items) == 2

    async def test_create_order_single_item(self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch):
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("99.99"))],
        )
        order = await order_service.create_order(session, order_in)
        assert order.total_amount == Decimal("99.99")
        result = await session.execute(select(Order).options(selectinload(Order.items)).where(Order.id == order.id))
        assert len(result.scalar_one().items) == 1

    async def test_create_order_total_calculation(self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch):
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(product_id=test_product_for_order.id, quantity=3, unit_price=Decimal("10.00")),
                OrderItemCreate(product_id=test_product_for_order.id, quantity=2, unit_price=Decimal("5.50")),
            ],
        )
        order = await order_service.create_order(session, order_in)
        assert order.total_amount == Decimal("41.00")

    async def test_create_order_dispatches_timeout_task(self, session: AsyncSession, test_user, test_product_for_order):
        from unittest.mock import patch

        with patch("app.modules.orders.service.dispatch") as mock_dispatch:
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("99.99"))],
            )
            order = await order_service.create_order(session, order_in)
            mock_dispatch.assert_called_once()
            assert mock_dispatch.call_args[0][1] == order.id
            assert "countdown" in mock_dispatch.call_args.kwargs


@pytest.mark.asyncio
class TestOrderServiceGet:
    async def test_get_order_by_id_found(self, session: AsyncSession, test_order):
        order = await order_service.get_order_by_id(session, test_order.id)
        assert order is not None
        assert order.id == test_order.id
        assert order.user_id == test_order.user_id

    async def test_get_order_by_id_not_found(self, session: AsyncSession):
        assert await order_service.get_order_by_id(session, 99999) is None

    async def test_get_order_with_items_found(self, session: AsyncSession, test_order):
        order = await order_service.get_order_with_items(session, test_order.id)
        assert order is not None
        assert len(order.items) > 0

    async def test_get_order_with_items_not_found(self, session: AsyncSession):
        assert await order_service.get_order_with_items(session, 99999) is None


@pytest.mark.asyncio
class TestOrderServiceList:
    async def test_get_orders_pagination(self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch):
        for _ in range(5):
            await order_service.create_order(session, OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            ))
        assert len(await order_service.get_orders(session, skip=0, limit=3)) == 3
        assert len(await order_service.get_orders(session, skip=3, limit=3)) >= 2

    async def test_get_orders_by_user(self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch):
        await order_service.create_order(session, OrderCreate(
            user_id=test_user.id,
            items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
        ))
        orders = await order_service.get_orders_by_user(session, test_user.id)
        assert len(orders) >= 1
        assert all(o.user_id == test_user.id for o in orders)

    async def test_get_orders_by_status(self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch):
        await order_service.create_order(session, OrderCreate(
            user_id=test_user.id,
            items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
        ))
        orders = await order_service.get_orders_by_status(session, OrderStatus.PENDING)
        assert len(orders) >= 1
        assert all(o.status == OrderStatus.PENDING.value for o in orders)

    async def test_get_orders_count(self, session: AsyncSession, test_user, test_product_for_order, patch_dispatch):
        initial = await order_service.get_orders_count(session)
        await order_service.create_order(session, OrderCreate(
            user_id=test_user.id,
            items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
        ))
        assert await order_service.get_orders_count(session) == initial + 1


@pytest.mark.asyncio
@pytest.mark.parametrize("before,after", [
    (OrderStatus.PENDING, OrderStatus.CONFIRMED),
    (OrderStatus.PENDING, OrderStatus.CANCELLED),
    (OrderStatus.CONFIRMED, OrderStatus.SHIPPED),
    (OrderStatus.CONFIRMED, OrderStatus.CANCELLED),
    (OrderStatus.SHIPPED, OrderStatus.COMPLETED),
])
class TestOrderServiceValidTransitions:
    async def test_valid_transition(self, session: AsyncSession, fresh_order, before, after):
        if fresh_order.status != before.value:
            fresh_order.status = before.value
            await session.commit()
        updated = await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=after))
        assert updated.status == after.value


@pytest.mark.asyncio
@pytest.mark.parametrize("before,invalid", [
    (OrderStatus.COMPLETED, OrderStatus.CANCELLED),
    (OrderStatus.COMPLETED, OrderStatus.PENDING),
    (OrderStatus.CANCELLED, OrderStatus.CONFIRMED),
    (OrderStatus.PENDING, OrderStatus.SHIPPED),
])
class TestOrderServiceInvalidTransitions:
    async def test_invalid_transition(self, session: AsyncSession, fresh_order, before, invalid):
        if fresh_order.status != before.value:
            fresh_order.status = before.value
            await session.commit()
        with pytest.raises(ValidationException):
            await order_service.update_order_status(session, fresh_order.id, OrderUpdate(status=invalid))

    async def test_update_order_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundException):
            await order_service.update_order_status(session, 99999, OrderUpdate(status=OrderStatus.CONFIRMED))


@pytest.mark.asyncio
class TestOrderServiceDelete:
    async def test_delete_order_found(self, session: AsyncSession, fresh_order):
        deleted = await order_service.delete_order(session, fresh_order.id)
        assert deleted.id == fresh_order.id
        assert await order_service.get_order_by_id(session, fresh_order.id) is None

    async def test_delete_order_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundException):
            await order_service.delete_order(session, 99999)
```

- [ ] **Step 2: Run orders service tests**
Run: `uv run pytest tests/modules/orders/test_order_service.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/modules/orders/test_order_service.py
git commit -m "test(orders): rewrite service tests with parametrize and fixtures"
```

---

## Task 4: Orders API Tests Rewrite

**Files:**

- Rewrite: `tests/modules/orders/test_order_api.py`

- [ ] **Step 1: Rewrite the file**

```python
from decimal import Decimal

import pytest
from fastapi import status

from app.modules.orders import service as order_service
from app.modules.orders.schemas import OrderCreate, OrderItemCreate


@pytest.mark.asyncio
class TestOrderAPICreate:
    async def test_create_order_success(self, client, user_headers, test_product_for_order, patch_dispatch):
        response = await client.post(
            "/api/v1/orders/",
            json={
                "user_id": 1,
                "items": [{"product_id": test_product_for_order.id, "quantity": 2, "unit_price": "99.99"}],
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_amount"] == "199.98"

    async def test_create_order_unauthorized(self, client, test_product_for_order):
        response = await client.post(
            "/api/v1/orders/",
            json={"user_id": 1, "items": [{"product_id": test_product_for_order.id, "quantity": 1, "unit_price": "50.00"}]},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_order_invalid_quantity(self, client, user_headers, test_product_for_order):
        response = await client.post(
            "/api/v1/orders/",
            json={"user_id": 1, "items": [{"product_id": test_product_for_order.id, "quantity": 0, "unit_price": "50.00"}]},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_order_invalid_price(self, client, user_headers, test_product_for_order):
        response = await client.post(
            "/api/v1/orders/",
            json={"user_id": 1, "items": [{"product_id": test_product_for_order.id, "quantity": 1, "unit_price": "-10.00"}]},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
class TestOrderAPIList:
    async def test_list_orders_admin_success(self, client, superuser_headers, test_order):
        response = await client.get("/api/v1/orders/", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data

    async def test_list_orders_pagination(self, client, superuser_headers, session, test_user, test_product_for_order, patch_dispatch):
        for _ in range(3):
            await order_service.create_order(session, OrderCreate(
                user_id=test_user.id,
                items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))],
            ))
        response = await client.get("/api/v1/orders/?page=1&page_size=2", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["data"]) == 2

    async def test_list_orders_filter_by_user(self, client, superuser_headers, test_order):
        response = await client.get(f"/api/v1/orders/?user_id={test_order.user_id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        for order in response.json()["data"]:
            assert order["user_id"] == test_order.user_id

    async def test_list_orders_filter_by_status(self, client, superuser_headers, test_order):
        response = await client.get("/api/v1/orders/?status=PENDING", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        for order in response.json()["data"]:
            assert order["status"].lower() == "pending"

    async def test_list_orders_unauthorized(self, client):
        assert (await client.get("/api/v1/orders/")).status_code == status.HTTP_401_UNAUTHORIZED

    async def test_list_orders_forbidden(self, client, user_headers):
        assert (await client.get("/api/v1/orders/", headers=user_headers)).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestOrderAPIMyOrders:
    async def test_my_orders_success(self, client, user_headers):
        response = await client.get("/api/v1/orders/my", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "data" in response.json()

    async def test_my_orders_unauthorized(self, client):
        assert (await client.get("/api/v1/orders/my")).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestOrderAPIGetById:
    async def test_get_order_by_id_found(self, client, user_headers, test_order):
        response = await client.get(f"/api/v1/orders/{test_order.id}", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["id"] == test_order.id

    async def test_get_order_by_id_not_found(self, client, user_headers):
        assert (await client.get("/api/v1/orders/99999", headers=user_headers)).status_code == status.HTTP_404_NOT_FOUND

    async def test_get_order_by_id_unauthorized(self, client, test_order):
        assert (await client.get(f"/api/v1/orders/{test_order.id}")).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestOrderAPIUpdate:
    async def test_update_order_admin_success(self, client, superuser_headers, test_order):
        response = await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "CONFIRMED"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["status"].lower() == "confirmed"

    async def test_update_order_invalid_transition(self, client, superuser_headers, test_order):
        response = await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "SHIPPED"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_update_order_forbidden(self, client, user_headers, test_order):
        assert (await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "CONFIRMED"},
            headers=user_headers,
        )).status_code == status.HTTP_403_FORBIDDEN

    async def test_update_order_unauthorized(self, client, test_order):
        assert (await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "CONFIRMED"},
        )).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestOrderAPIDelete:
    async def test_delete_order_admin_success(self, client, superuser_headers, test_order):
        assert (await client.delete(
            f"/api/v1/orders/{test_order.id}",
            headers=superuser_headers,
        )).status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_order_forbidden(self, client, user_headers, test_order):
        assert (await client.delete(
            f"/api/v1/orders/{test_order.id}",
            headers=user_headers,
        )).status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_order_unauthorized(self, client, test_order):
        assert (await client.delete(
            f"/api/v1/orders/{test_order.id}",
        )).status_code == status.HTTP_401_UNAUTHORIZED
```

- [ ] **Step 2: Run orders API tests**
Run: `uv run pytest tests/modules/orders/test_order_api.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/modules/orders/test_order_api.py
git commit -m "test(orders): rewrite API tests with patch_dispatch and cleaner assertions"
```

---

## Task 5: Products conftest.py Cleanup

**Files:**

- Modify: `tests/modules/products/conftest.py`

- [ ] **Step 1: Remove duplicated fixtures**

Remove `superuser_headers` and `user_headers` from the file. Final result:

```python
import uuid
from decimal import Decimal

import pytest_asyncio

from app.modules.products import service as product_service
from app.modules.products.schemas import ProductCreate


@pytest_asyncio.fixture
async def test_product(session):
    product_in = ProductCreate(
        name="Test Product",
        sku=f"TEST-{uuid.uuid4().hex[:8]}",
        description="A test product",
        price=Decimal("99.99"),
        category="test",
    )
    return await product_service.create_product(session, product_in)


@pytest_asyncio.fixture
async def multiple_products(session):
    products = []
    categories = ["electronics", "clothing", "electronics", "books", "food"]
    for i in range(5):
        product_in = ProductCreate(
            name=f"Product {i + 1}",
            sku=f"MULTI-{uuid.uuid4().hex[:8]}-{i}",
            description=f"Test product {i + 1}",
            price=Decimal(f"{(i + 1) * 10}.00"),
            category=categories[i],
        )
        products.append(await product_service.create_product(session, product_in))
    return products
```

- [ ] **Step 2: Run products tests**
Run: `uv run pytest tests/modules/products -v`
Expected: All tests PASS (fixtures resolved from root conftest)

- [ ] **Step 3: Commit**

```bash
git add tests/modules/products/conftest.py
git commit -m "test(products): remove duplicated fixtures, use root conftest"
```

---

## Task 6: Products Service Tests Cleanup

**Files:**

- Modify: `tests/modules/products/test_product_service.py`

- [ ] **Step 1: Fix imports and clean up**

Changes:

1. Add `session: AsyncSession` type hints
2. Add `import uuid` at file top (already there, verify)
3. Remove unused `ValidationError` import (keep only if used)
4. Ensure consistent naming

Final file:

```python
import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.products import service as product_service
from app.modules.products.schemas import ProductCreate, ProductUpdate


@pytest.mark.asyncio
class TestProductServiceCreate:
    async def test_create_product_success(self, session: AsyncSession):
        product_in = ProductCreate(
            name="New Product",
            sku=f"NEW-{uuid.uuid4().hex[:8]}",
            description="A new product",
            price=Decimal("49.99"),
            category="new",
        )
        product = await product_service.create_product(session, product_in)
        assert product.id is not None
        assert product.name == product_in.name
        assert product.sku == product_in.sku
        assert product.price == product_in.price
        assert product.category == product_in.category
        assert product.is_active is True

    async def test_create_product_duplicate_sku(self, session: AsyncSession, test_product):
        with pytest.raises(ConflictException):
            await product_service.create_product(session, ProductCreate(
                name="Duplicate",
                sku=test_product.sku,
                price=Decimal("19.99"),
            ))

    async def test_create_product_negative_price(self, session: AsyncSession):
        with pytest.raises(ValidationError):
            ProductCreate(
                name="Negative",
                sku=f"NEG-{uuid.uuid4().hex[:8]}",
                price=Decimal("-10.00"),
            )


@pytest.mark.asyncio
class TestProductServiceGet:
    async def test_get_product_by_id_found(self, session: AsyncSession, test_product):
        product = await product_service.get_product_by_id(session, test_product.id)
        assert product is not None
        assert product.id == test_product.id
        assert product.sku == test_product.sku

    async def test_get_product_by_id_not_found(self, session: AsyncSession):
        assert await product_service.get_product_by_id(session, 99999) is None

    async def test_get_product_by_sku_found(self, session: AsyncSession, test_product):
        product = await product_service.get_product_by_sku(session, test_product.sku)
        assert product is not None
        assert product.id == test_product.id

    async def test_get_product_by_sku_not_found(self, session: AsyncSession):
        assert await product_service.get_product_by_sku(session, "NONEXISTENT-SKU") is None


@pytest.mark.asyncio
class TestProductServiceList:
    async def test_get_products_pagination(self, session: AsyncSession, multiple_products):
        assert len(await product_service.get_products(session, skip=0, limit=3)) == 3
        assert len(await product_service.get_products(session, skip=3, limit=3)) >= 2

    async def test_get_products_by_category(self, session: AsyncSession, multiple_products):
        products = await product_service.get_products_by_category(session, "electronics", skip=0, limit=100)
        assert len(products) >= 2
        assert all(p.category == "electronics" for p in products)

    async def test_get_products_count(self, session: AsyncSession, multiple_products):
        assert await product_service.get_products_count(session) >= 5


@pytest.mark.asyncio
class TestProductServiceUpdate:
    async def test_update_product_success(self, session: AsyncSession, test_product):
        product = await product_service.update_product(
            session, test_product.id,
            ProductUpdate(name="Updated", price=Decimal("149.99"))
        )
        assert product.name == "Updated"
        assert product.price == Decimal("149.99")
        assert product.sku == test_product.sku

    async def test_update_product_partial(self, session: AsyncSession, test_product):
        product = await product_service.update_product(
            session, test_product.id,
            ProductUpdate(description="Updated description only")
        )
        assert product.description == "Updated description only"
        assert product.name == test_product.name

    async def test_update_product_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundException):
            await product_service.update_product(session, 99999, ProductUpdate(name="X"))


@pytest.mark.asyncio
class TestProductServiceDelete:
    async def test_delete_product_found(self, session: AsyncSession):
        product_in = ProductCreate(
            name="To Delete",
            sku=f"DEL-{uuid.uuid4().hex[:8]}",
            price=Decimal("19.99"),
        )
        product = await product_service.create_product(session, product_in)
        deleted = await product_service.delete_product(session, product.id)
        assert deleted.id == product.id
        assert await product_service.get_product_by_id(session, product.id) is None

    async def test_delete_product_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundException):
            await product_service.delete_product(session, 99999)
```

- [ ] **Step 2: Run tests**
Run: `uv run pytest tests/modules/products/test_product_service.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/modules/products/test_product_service.py
git commit -m "test(products): add type hints and clean up service tests"
```

---

## Task 7: Products API Tests Cleanup

**Files:**

- Modify: `tests/modules/products/test_product_api.py`

- [ ] **Step 1: Fix status code assertions**

Key changes:

1. Remove unused `ProductCreate` import
2. Remove unused `uuid` import (only used in test data)
3. Verify status codes are specific (not lists)

```python
import uuid

import pytest
from fastapi import status


@pytest.mark.asyncio
class TestProductAPICreate:
    async def test_create_product_admin_success(self, client, superuser_headers):
        response = await client.post(
            "/api/v1/products/",
            json={
                "name": "API Test Product",
                "sku": f"API-{uuid.uuid4().hex[:8]}",
                "description": "Created via API",
                "price": "79.99",
                "category": "api-test",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "API Test Product"

    async def test_create_product_forbidden(self, client, user_headers):
        response = await client.post(
            "/api/v1/products/",
            json={
                "name": "Forbidden",
                "sku": f"FORB-{uuid.uuid4().hex[:8]}",
                "price": "19.99",
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_create_product_unauthorized(self, client):
        response = await client.post(
            "/api/v1/products/",
            json={"name": "Unauthorized", "sku": f"UNAUTH-{uuid.uuid4().hex[:8]}", "price": "19.99"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestProductAPIList:
    async def test_get_products_authenticated_success(self, client, user_headers, test_product):
        response = await client.get("/api/v1/products/", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "data" in response.json()
        assert "total" in response.json()

    async def test_get_products_filter_by_category(self, client, user_headers, multiple_products):
        response = await client.get("/api/v1/products/?category=electronics", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        for product in response.json()["data"]:
            assert product["category"] == "electronics"

    async def test_get_products_unauthorized(self, client):
        assert (await client.get("/api/v1/products/")).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestProductAPIGetById:
    async def test_get_product_by_id_found(self, client, user_headers, test_product):
        response = await client.get(f"/api/v1/products/{test_product.id}", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["id"] == test_product.id

    async def test_get_product_by_id_not_found(self, client, user_headers):
        assert (await client.get("/api/v1/products/99999", headers=user_headers)).status_code == status.HTTP_404_NOT_FOUND

    async def test_get_product_by_sku_found(self, client, user_headers, test_product):
        response = await client.get(f"/api/v1/products/sku/{test_product.sku}", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["sku"] == test_product.sku

    async def test_get_product_by_sku_not_found(self, client, user_headers):
        assert (await client.get("/api/v1/products/sku/NONEXISTENT-SKU", headers=user_headers)).status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
class TestProductAPIUpdate:
    async def test_update_product_admin_success(self, client, superuser_headers, test_product):
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            json={"name": "Updated via API", "price": "199.99"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["name"] == "Updated via API"

    async def test_update_product_forbidden(self, client, user_headers, test_product):
        assert (await client.put(
            f"/api/v1/products/{test_product.id}",
            json={"name": "Forbidden"},
            headers=user_headers,
        )).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestProductAPIDelete:
    async def test_delete_product_admin_success(self, client, superuser_headers):
        product_sku = f"DEL-API-{uuid.uuid4().hex[:8]}"
        create_resp = await client.post(
            "/api/v1/products/",
            json={"name": "To Delete", "sku": product_sku, "price": "29.99", "category": "test"},
            headers=superuser_headers,
        )
        product_id = create_resp.json()["data"]["id"]
        assert (await client.delete(f"/api/v1/products/{product_id}", headers=superuser_headers)).status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_product_forbidden(self, client, user_headers, test_product):
        assert (await client.delete(
            f"/api/v1/products/{test_product.id}",
            headers=user_headers,
        )).status_code == status.HTTP_403_FORBIDDEN
```

- [ ] **Step 2: Run tests**
Run: `uv run pytest tests/modules/products/test_product_api.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/modules/products/test_product_api.py
git commit -m "test(products): clean up API tests, fix unused imports"
```

---

## Task 8: Audit conftest.py Cleanup

**Files:**

- Modify: `tests/modules/audit/conftest.py`

- [ ] **Step 1: Remove duplicated fixtures**

Remove `superuser_headers` and `user_headers`. Final result:

```python
import pytest_asyncio

from app.modules.audit import service as audit_service
from app.modules.audit.schemas import AuditLogCreate


@pytest_asyncio.fixture
async def test_audit_log(session):
    audit_in = AuditLogCreate(
        user_id=1,
        action="create",
        resource_type="product",
        resource_id=1,
        old_value=None,
        new_value='{"name": "Test Product"}',
        ip_address="127.0.0.1",
    )
    return await audit_service.create_audit_log(session, audit_in)


@pytest_asyncio.fixture
async def multiple_audit_logs(session):
    logs = []
    actions = ["create", "update", "delete", "create", "update"]
    for i in range(5):
        audit_in = AuditLogCreate(
            user_id=i + 1,
            action=actions[i],
            resource_type="product" if i % 2 == 0 else "order",
            resource_id=i + 1,
            old_value='{"old": "value"}' if i % 2 == 1 else None,
            new_value=f'{{"new": "value{i}"}}',
            ip_address=f"192.168.1.{i}",
        )
        logs.append(await audit_service.create_audit_log(session, audit_in))
    return logs
```

- [ ] **Step 2: Run audit tests**
Run: `uv run pytest tests/modules/audit -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/modules/audit/conftest.py
git commit -m "test(audit): remove duplicated fixtures, use root conftest"
```

---

## Task 9: Audit Tests Cleanup

**Files:**

- Modify: `tests/modules/audit/test_audit_service.py`
- Modify: `tests/modules/audit/test_audit_api.py`

- [ ] **Step 1: Clean up audit service tests**

Add `@pytest.mark.asyncio` to test classes (audit tests currently lack it):

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit import service as audit_service
from app.modules.audit.schemas import AuditLogCreate


@pytest.mark.asyncio
class TestAuditServiceCreate:
    async def test_create_audit_log_success(self, session: AsyncSession):
        audit_in = AuditLogCreate(
            user_id=1,
            action="create",
            resource_type="product",
            resource_id=1,
            old_value=None,
            new_value='{"name": "Test Product"}',
            ip_address="127.0.0.1",
        )
        result = await audit_service.create_audit_log(session, audit_in)
        assert result.id is not None
        assert result.user_id == 1
        assert result.action == "create"
        assert result.resource_type == "product"
        assert result.resource_id == 1
        assert result.ip_address == "127.0.0.1"

    async def test_create_audit_log_without_user_id(self, session: AsyncSession):
        audit_in = AuditLogCreate(
            user_id=None,
            action="system_refresh",
            resource_type="cache",
            resource_id=0,
            ip_address=None,
        )
        result = await audit_service.create_audit_log(session, audit_in)
        assert result.user_id is None
        assert result.action == "system_refresh"

    async def test_create_audit_log_minimal(self, session: AsyncSession):
        audit_in = AuditLogCreate(
            action="login",
            resource_type="session",
            resource_id=1,
        )
        result = await audit_service.create_audit_log(session, audit_in)
        assert result.id is not None
        assert result.user_id is None
        assert result.old_value is None
        assert result.ip_address is None


@pytest.mark.asyncio
class TestAuditServiceGet:
    async def test_get_audit_log_by_id_found(self, session: AsyncSession, test_audit_log):
        result = await audit_service.get_audit_log_by_id(session, test_audit_log.id)
        assert result is not None
        assert result.id == test_audit_log.id

    async def test_get_audit_log_by_id_not_found(self, session: AsyncSession):
        assert await audit_service.get_audit_log_by_id(session, 99999) is None


@pytest.mark.asyncio
class TestAuditServiceList:
    async def test_get_audit_logs_pagination(self, session: AsyncSession, multiple_audit_logs):
        page1 = await audit_service.get_audit_logs(session, skip=0, limit=2)
        page2 = await audit_service.get_audit_logs(session, skip=2, limit=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    async def test_get_audit_logs_by_user(self, session: AsyncSession):
        for i in range(3):
            await audit_service.create_audit_log(session, AuditLogCreate(
                user_id=42, action="update", resource_type="user", resource_id=i + 1
            ))
        await audit_service.create_audit_log(session, AuditLogCreate(
            user_id=99, action="delete", resource_type="user", resource_id=100
        ))
        results = await audit_service.get_audit_logs_by_user(session, 42)
        assert len(results) == 3
        assert all(log.user_id == 42 for log in results)

    async def test_get_audit_logs_by_resource(self, session: AsyncSession):
        for _ in range(3):
            await audit_service.create_audit_log(session, AuditLogCreate(
                user_id=1, action="create", resource_type="order", resource_id=500
            ))
        await audit_service.create_audit_log(session, AuditLogCreate(
            user_id=1, action="create", resource_type="order", resource_id=501
        ))
        results = await audit_service.get_audit_logs_by_resource(session, "order", 500)
        assert len(results) == 3
        assert all(log.resource_id == 500 for log in results)

    async def test_get_audit_logs_count(self, session: AsyncSession, multiple_audit_logs):
        assert await audit_service.get_audit_logs_count(session) >= 5
```

- [ ] **Step 2: Clean up audit API tests**

```python
import pytest
from fastapi import status


@pytest.mark.asyncio
class TestAuditAPIList:
    async def test_get_audit_logs_admin_success(self, client, superuser_headers):
        response = await client.get("/api/v1/audit/", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data

    async def test_get_audit_logs_filter_by_user(self, client, superuser_headers, multiple_audit_logs):
        response = await client.get("/api/v1/audit/?user_id=1", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        for log in response.json()["data"]:
            assert log["user_id"] == 1

    async def test_get_audit_logs_filter_by_resource(self, client, superuser_headers):
        response = await client.get("/api/v1/audit/?resource_type=product&resource_id=1", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "data" in response.json()

    async def test_get_audit_logs_unauthorized(self, client):
        assert (await client.get("/api/v1/audit/")).status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_audit_logs_forbidden(self, client, user_headers):
        assert (await client.get("/api/v1/audit/", headers=user_headers)).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestAuditAPIGetById:
    async def test_get_audit_log_by_id_admin_success(self, client, superuser_headers, test_audit_log):
        response = await client.get(f"/api/v1/audit/{test_audit_log.id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["id"] == test_audit_log.id

    async def test_get_audit_log_by_id_not_found(self, client, superuser_headers):
        assert (await client.get("/api/v1/audit/99999", headers=superuser_headers)).status_code == status.HTTP_404_NOT_FOUND

    async def test_get_audit_log_by_id_unauthorized(self, client):
        assert (await client.get("/api/v1/audit/1")).status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_audit_log_by_id_forbidden(self, client, user_headers):
        assert (await client.get("/api/v1/audit/1", headers=user_headers)).status_code == status.HTTP_403_FORBIDDEN
```

- [ ] **Step 3: Run audit tests**
Run: `uv run pytest tests/modules/audit -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/modules/audit/test_audit_service.py tests/modules/audit/test_audit_api.py
git commit -m "test(audit): add async markers, type hints, and clean up assertions"
```

---

## Task 10: Roles Tests - Fix import uuid

**Files:**

- Modify: `tests/modules/roles/test_role_service.py`
- Modify: `tests/modules/roles/test_permission_service.py`

- [ ] **Step 1: Fix test_role_service.py**

Move `import uuid` from inside test methods to file top. Remove all `import uuid` lines inside test bodies.

```python
import uuid

import pytest

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.roles import service as role_service
from app.modules.roles.schemas import RoleCreate, RoleUpdate


@pytest.mark.asyncio
class TestRoleService:
    async def test_create_role_success(self, session):
        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"test_role_{unique_id}", description="Test role")
        role = await role_service.create_role(session, role_in)
        assert role.name == f"test_role_{unique_id}"
        assert role.description == "Test role"

    # ... rest of tests with import uuid removed from inside methods
```

- [ ] **Step 2: Fix test_permission_service.py**

Same fix - move `import uuid` to file top.

- [ ] **Step 3: Run roles tests**
Run: `uv run pytest tests/modules/roles -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/modules/roles/test_role_service.py tests/modules/roles/test_permission_service.py
git commit -m "test(roles): move import uuid to file top level"
```

---

## Task 11: Final Verification

- [ ] **Step 1: Run full test suite**
Run: `uv run pytest tests -v --tb=short`
Expected: All 147+ tests PASS

- [ ] **Step 2: Verify no unused imports**
Run: `uv run ruff check tests/`
Expected: No errors

- [ ] **Step 3: Run ruff format**
Run: `uv run ruff format tests/`
Expected: Clean formatting

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "test: complete test code refactoring with consistent patterns"
```

---

## Summary

**Tasks:** 11
**Files Modified:** 13
**Files Created:** 2 (helpers.py, updated conftest.py)
**Expected Result:** 147+ tests passing, no duplication, consistent patterns
