# Comprehensive Test Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add comprehensive service and API tests for Orders, Products, and Audit modules with 110+ test cases.

**Architecture:** Follow existing test patterns from users and roles modules. Create module-specific fixtures, service tests for business logic, and API tests for endpoints. Use in-memory SQLite with async sessions.

**Tech Stack:** pytest, pytest-asyncio, httpx, SQLAlchemy async, Pydantic

**Spec:** `docs/superpowers/specs/2026-03-26-comprehensive-test-coverage-design.md`

---

## File Structure

```text
tests/modules/
├── orders/
│   ├── __init__.py              # Create
│   ├── conftest.py              # Create - order/product fixtures
│   ├── test_order_service.py    # Create - 25 service tests
│   └── test_order_api.py        # Create - 20 API tests
├── products/
│   ├── __init__.py              # Create
│   ├── conftest.py              # Create - product fixtures
│   ├── test_product_service.py  # Create - 20 service tests
│   └── test_product_api.py      # Create - 18 API tests
└── audit/
    ├── __init__.py              # Create
    ├── conftest.py              # Create - audit log fixtures
    ├── test_audit_service.py    # Create - 15 service tests
    └── test_audit_api.py        # Create - 12 API tests
```

---

## Module 1: Orders Tests

### Task 1: Orders Module Setup

**Files:**

- Create: `tests/modules/orders/__init__.py`
- Create: `tests/modules/orders/conftest.py`

- [ ] **Step 1: Create orders test directory**

```bash
mkdir -p tests/modules/orders
touch tests/modules/orders/__init__.py
```

- [ ] **Step 2: Create orders conftest.py with fixtures**

```python
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio

from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from app.modules.orders import service as order_service
from app.modules.products.schemas import ProductCreate
from app.modules.products import service as product_service


@pytest_asyncio.fixture
async def test_product_for_order(session):
    """Create a product for order tests."""
    product_in = ProductCreate(
        name="Test Product for Order",
        sku=f"TEST-ORDER-{uuid.uuid4().hex[:8]}",
        price=Decimal("99.99"),
        category="test"
    )
    return await product_service.create_product(session, product_in)


@pytest_asyncio.fixture
async def test_order(session, test_user, test_product_for_order):
    """Create a test order with items."""
    order_in = OrderCreate(
        user_id=test_user.id,
        items=[
            OrderItemCreate(
                product_id=test_product_for_order.id,
                quantity=2,
                unit_price=test_product_for_order.price
            )
        ]
    )
    return await order_service.create_order(session, order_in)


@pytest_asyncio.fixture
async def superuser_headers(superuser_token):
    """Headers for admin API calls."""
    return {"Authorization": f"Bearer {superuser_token}"}


@pytest_asyncio.fixture
async def user_headers(user_token):
    """Headers for regular user API calls."""
    return {"Authorization": f"Bearer {user_token}"}
```

- [ ] **Step 3: Commit orders setup**

```bash
git add tests/modules/orders/__init__.py tests/modules/orders/conftest.py
git commit -m "test(orders): add test fixtures for orders module"
```

---

### Task 2: Order Service Tests - Create Operations

**Files:**

- Create: `tests/modules/orders/test_order_service.py`

- [ ] **Step 1: Create test file with imports and class**

```python
import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.orders import service as order_service
from app.modules.orders.models import OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderItemCreate, OrderUpdate
from app.modules.products.schemas import ProductCreate
from app.modules.products import service as product_service


@pytest.mark.asyncio
class TestOrderServiceCreate:
    """Tests for order creation."""
```

- [ ] **Step 2: Add test_create_order_success**

```python
    async def test_create_order_success(self, session, test_user, test_product_for_order):
        """Test successful order creation with multiple items."""
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(
                    product_id=test_product_for_order.id,
                    quantity=2,
                    unit_price=Decimal("99.99")
                ),
                OrderItemCreate(
                    product_id=test_product_for_order.id,
                    quantity=1,
                    unit_price=Decimal("50.00")
                )
            ]
        )
        order = await order_service.create_order(session, order_in)

        assert order.id is not None
        assert order.user_id == test_user.id
        assert order.status == OrderStatus.PENDING.value
        assert order.total_amount == Decimal("249.98")  # 2*99.99 + 1*50.00
        assert len(order.items) == 2
```

- [ ] **Step 3: Add test_create_order_single_item**

```python
    async def test_create_order_single_item(self, session, test_user, test_product_for_order):
        """Test order creation with single item."""
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(
                    product_id=test_product_for_order.id,
                    quantity=1,
                    unit_price=Decimal("99.99")
                )
            ]
        )
        order = await order_service.create_order(session, order_in)

        assert order.id is not None
        assert len(order.items) == 1
        assert order.total_amount == Decimal("99.99")
```

- [ ] **Step 4: Add test_create_order_total_calculation**

```python
    async def test_create_order_total_calculation(self, session, test_user, test_product_for_order):
        """Test total amount is calculated correctly."""
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(product_id=test_product_for_order.id, quantity=3, unit_price=Decimal("10.00")),
                OrderItemCreate(product_id=test_product_for_order.id, quantity=2, unit_price=Decimal("5.50")),
            ]
        )
        order = await order_service.create_order(session, order_in)

        assert order.total_amount == Decimal("41.00")  # 3*10 + 2*5.50
```

- [ ] **Step 5: Add test_create_order_dispatches_timeout_task**

```python
    async def test_create_order_dispatches_timeout_task(self, session, test_user, test_product_for_order):
        """Test that timeout cancellation task is dispatched."""
        with patch("app.modules.orders.service.dispatch") as mock_dispatch:
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[
                    OrderItemCreate(
                        product_id=test_product_for_order.id,
                        quantity=1,
                        unit_price=Decimal("99.99")
                    )
                ]
            )
            order = await order_service.create_order(session, order_in)

            mock_dispatch.assert_called_once()
            call_args = mock_dispatch.call_args
            assert call_args[0][0].__name__ == "cancel_timeout"
            assert call_args[0][1] == order.id
            assert "countdown" in call_args.kwargs
```

- [ ] **Step 6: Run tests to verify they pass**
Run: `uv run pytest tests/modules/orders/test_order_service.py::TestOrderServiceCreate -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add tests/modules/orders/test_order_service.py
git commit -m "test(orders): add service tests for order creation"
```

---

### Task 3: Order Service Tests - Get Operations

**Files:**

- Modify: `tests/modules/orders/test_order_service.py`

- [ ] **Step 1: Add TestOrderServiceGet class**

```python
@pytest.mark.asyncio
class TestOrderServiceGet:
    """Tests for order retrieval."""
```

- [ ] **Step 2: Add test_get_order_by_id_found**

```python
    async def test_get_order_by_id_found(self, session, test_order):
        """Test getting order by ID when it exists."""
        order = await order_service.get_order_by_id(session, test_order.id)

        assert order is not None
        assert order.id == test_order.id
        assert order.user_id == test_order.user_id
```

- [ ] **Step 3: Add test_get_order_by_id_not_found**

```python
    async def test_get_order_by_id_not_found(self, session):
        """Test getting order by ID when it doesn't exist."""
        order = await order_service.get_order_by_id(session, 99999)

        assert order is None
```

- [ ] **Step 4: Add test_get_order_with_items_found**

```python
    async def test_get_order_with_items_found(self, session, test_order):
        """Test getting order with items loaded."""
        order = await order_service.get_order_with_items(session, test_order.id)

        assert order is not None
        assert order.id == test_order.id
        assert len(order.items) > 0
```

- [ ] **Step 5: Add test_get_order_with_items_not_found**

```python
    async def test_get_order_with_items_not_found(self, session):
        """Test getting order with items when order doesn't exist."""
        order = await order_service.get_order_with_items(session, 99999)

        assert order is None
```

- [ ] **Step 6: Run tests**
Run: `uv run pytest tests/modules/orders/test_order_service.py::TestOrderServiceGet -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add tests/modules/orders/test_order_service.py
git commit -m "test(orders): add service tests for order retrieval"
```

---

### Task 4: Order Service Tests - List Operations

**Files:**

- Modify: `tests/modules/orders/test_order_service.py`

- [ ] **Step 1: Add TestOrderServiceList class**

```python
@pytest.mark.asyncio
class TestOrderServiceList:
    """Tests for order listing."""
```

- [ ] **Step 2: Add test_get_orders_pagination**

```python
    async def test_get_orders_pagination(self, session, test_user, test_product_for_order):
        """Test order listing with pagination."""
        for i in range(5):
            order_in = OrderCreate(
                user_id=test_user.id,
                items=[
                    OrderItemCreate(
                        product_id=test_product_for_order.id,
                        quantity=1,
                        unit_price=Decimal("10.00")
                    )
                ]
            )
            await order_service.create_order(session, order_in)

        page1 = await order_service.get_orders(session, skip=0, limit=2)
        page2 = await order_service.get_orders(session, skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
```

- [ ] **Step 3: Add test_get_orders_by_user**

```python
    async def test_get_orders_by_user(self, session, test_user, test_product_for_order):
        """Test filtering orders by user."""
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(
                    product_id=test_product_for_order.id,
                    quantity=1,
                    unit_price=Decimal("10.00")
                )
            ]
        )
        await order_service.create_order(session, order_in)

        orders = await order_service.get_orders_by_user(session, test_user.id)

        assert len(orders) >= 1
        assert all(o.user_id == test_user.id for o in orders)
```

- [ ] **Step 4: Add test_get_orders_by_status**

```python
    async def test_get_orders_by_status(self, session, test_user, test_product_for_order):
        """Test filtering orders by status."""
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(
                    product_id=test_product_for_order.id,
                    quantity=1,
                    unit_price=Decimal("10.00")
                )
            ]
        )
        order = await order_service.create_order(session, order_in)

        pending_orders = await order_service.get_orders_by_status(session, OrderStatus.PENDING)

        assert len(pending_orders) >= 1
        assert all(o.status == OrderStatus.PENDING.value for o in pending_orders)
```

- [ ] **Step 5: Add test_get_orders_count**

```python
    async def test_get_orders_count(self, session, test_user, test_product_for_order):
        """Test order count."""
        initial_count = await order_service.get_orders_count(session)

        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(
                    product_id=test_product_for_order.id,
                    quantity=1,
                    unit_price=Decimal("10.00")
                )
            ]
        )
        await order_service.create_order(session, order_in)

        new_count = await order_service.get_orders_count(session)
        assert new_count == initial_count + 1
```

- [ ] **Step 6: Run tests**
Run: `uv run pytest tests/modules/orders/test_order_service.py::TestOrderServiceList -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add tests/modules/orders/test_order_service.py
git commit -m "test(orders): add service tests for order listing"
```

---

### Task 5: Order Service Tests - Status Transitions

**Files:**

- Modify: `tests/modules/orders/test_order_service.py`

- [ ] **Step 1: Add TestOrderServiceStatusTransitions class**

```python
@pytest.mark.asyncio
class TestOrderServiceStatusTransitions:
    """Tests for order status transitions."""
```

- [ ] **Step 2: Add valid transition tests**

```python
    async def test_update_status_pending_to_confirmed(self, session, test_order):
        """Test valid transition: PENDING -> CONFIRMED."""
        update = OrderUpdate(status=OrderStatus.CONFIRMED)
        order = await order_service.update_order_status(session, test_order.id, update)
        assert order.status == OrderStatus.CONFIRMED.value

    async def test_update_status_pending_to_cancelled(self, session, test_order):
        """Test valid transition: PENDING -> CANCELLED."""
        update = OrderUpdate(status=OrderStatus.CANCELLED)
        order = await order_service.update_order_status(session, test_order.id, update)
        assert order.status == OrderStatus.CANCELLED.value

    async def test_update_status_confirmed_to_shipped(self, session, test_order):
        """Test valid transition: CONFIRMED -> SHIPPED."""
        test_order.status = OrderStatus.CONFIRMED.value
        await session.commit()
        update = OrderUpdate(status=OrderStatus.SHIPPED)
        order = await order_service.update_order_status(session, test_order.id, update)
        assert order.status == OrderStatus.SHIPPED.value

    async def test_update_status_confirmed_to_cancelled(self, session, test_order):
        """Test valid transition: CONFIRMED -> CANCELLED."""
        test_order.status = OrderStatus.CONFIRMED.value
        await session.commit()
        update = OrderUpdate(status=OrderStatus.CANCELLED)
        order = await order_service.update_order_status(session, test_order.id, update)
        assert order.status == OrderStatus.CANCELLED.value

    async def test_update_status_shipped_to_completed(self, session, test_order):
        """Test valid transition: SHIPPED -> COMPLETED."""
        test_order.status = OrderStatus.SHIPPED.value
        await session.commit()
        update = OrderUpdate(status=OrderStatus.COMPLETED)
        order = await order_service.update_order_status(session, test_order.id, update)
        assert order.status == OrderStatus.COMPLETED.value
```

- [ ] **Step 3: Add invalid transition tests**

```python
    async def test_update_status_completed_to_any_fails(self, session, test_order):
        """Test invalid transition: COMPLETED -> PENDING."""
        test_order.status = OrderStatus.COMPLETED.value
        await session.commit()

        with pytest.raises(ValidationException) as exc_info:
            await order_service.update_order_status(
                session, test_order.id, OrderUpdate(status=OrderStatus.PENDING)
            )
        assert "Cannot transition" in str(exc_info.value)

    async def test_update_status_cancelled_to_any_fails(self, session, test_order):
        """Test invalid transition: CANCELLED -> PENDING."""
        test_order.status = OrderStatus.CANCELLED.value
        await session.commit()

        with pytest.raises(ValidationException) as exc_info:
            await order_service.update_order_status(
                session, test_order.id, OrderUpdate(status=OrderStatus.PENDING)
            )
        assert "Cannot transition" in str(exc_info.value)

    async def test_update_status_pending_to_shipped_fails(self, session, test_order):
        """Test invalid transition: PENDING -> SHIPPED (skip)."""
        with pytest.raises(ValidationException) as exc_info:
            await order_service.update_order_status(
                session, test_order.id, OrderUpdate(status=OrderStatus.SHIPPED)
            )
        assert "Cannot transition" in str(exc_info.value)
```

- [ ] **Step 4: Add not found test**

```python
    async def test_update_status_order_not_found(self, session):
        """Test updating non-existent order."""
        with pytest.raises(NotFoundException) as exc_info:
            await order_service.update_order_status(
                session, 99999, OrderUpdate(status=OrderStatus.CONFIRMED)
            )
        assert "not found" in str(exc_info.value)
```

- [ ] **Step 5: Run tests**
Run: `uv run pytest tests/modules/orders/test_order_service.py::TestOrderServiceStatusTransitions -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/modules/orders/test_order_service.py
git commit -m "test(orders): add service tests for status transitions"
```

---

### Task 6: Order Service Tests - Delete Operations

**Files:**

- Modify: `tests/modules/orders/test_order_service.py`

- [ ] **Step 1: Add TestOrderServiceDelete class**

```python
@pytest.mark.asyncio
class TestOrderServiceDelete:
    """Tests for order deletion."""
```

- [ ] **Step 2: Add test_delete_order_found**

```python
    async def test_delete_order_found(self, session, test_user, test_product_for_order):
        """Test deleting an existing order."""
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(
                    product_id=test_product_for_order.id,
                    quantity=1,
                    unit_price=Decimal("10.00")
                )
            ]
        )
        order = await order_service.create_order(session, order_in)

        deleted = await order_service.delete_order(session, order.id)

        assert deleted.id == order.id

        # Verify it's deleted
        result = await order_service.get_order_by_id(session, order.id)
        assert result is None
```

- [ ] **Step 3: Add test_delete_order_not_found**

```python
    async def test_delete_order_not_found(self, session):
        """Test deleting non-existent order."""
        with pytest.raises(NotFoundException) as exc_info:
            await order_service.delete_order(session, 99999)
        assert "not found" in str(exc_info.value)
```

- [ ] **Step 4: Run tests**
Run: `uv run pytest tests/modules/orders/test_order_service.py::TestOrderServiceDelete -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/modules/orders/test_order_service.py
git commit -m "test(orders): add service tests for order deletion"
```

---

### Task 7: Order API Tests - Create Endpoint

**Files:**

- Create: `tests/modules/orders/test_order_api.py`

- [ ] **Step 1: Create test file with imports**

```python
from decimal import Decimal

import pytest
from fastapi import status


@pytest.mark.asyncio
class TestOrderAPICreate:
    """Tests for POST /api/v1/orders endpoint."""
```

- [ ] **Step 2: Add test_create_order_success**

```python
    async def test_create_order_success(self, client, user_headers, test_product_for_order):
        """Test successful order creation via API."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": 1,
                "items": [
                    {
                        "product_id": test_product_for_order.id,
                        "quantity": 2,
                        "unit_price": "99.99"
                    }
                ]
            },
            headers=user_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["status"] == "PENDING"
```

- [ ] **Step 3: Add test_create_order_unauthorized**

```python
    async def test_create_order_unauthorized(self, client, test_product_for_order):
        """Test order creation without authentication."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": 1,
                "items": [
                    {
                        "product_id": test_product_for_order.id,
                        "quantity": 1,
                        "unit_price": "10.00"
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

- [ ] **Step 4: Add test_create_order_invalid_quantity**

```python
    async def test_create_order_invalid_quantity(self, client, user_headers, test_product_for_order):
        """Test order creation with invalid quantity."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": 1,
                "items": [
                    {
                        "product_id": test_product_for_order.id,
                        "quantity": 0,
                        "unit_price": "10.00"
                    }
                ]
            },
            headers=user_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

- [ ] **Step 5: Add test_create_order_invalid_price**

```python
    async def test_create_order_invalid_price(self, client, user_headers, test_product_for_order):
        """Test order creation with invalid price."""
        response = await client.post(
            "/api/v1/orders",
            json={
                "user_id": 1,
                "items": [
                    {
                        "product_id": test_product_for_order.id,
                        "quantity": 1,
                        "unit_price": "-10.00"
                    }
                ]
            },
            headers=user_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

- [ ] **Step 6: Run tests**
Run: `uv run pytest tests/modules/orders/test_order_api.py::TestOrderAPICreate -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add tests/modules/orders/test_order_api.py
git commit -m "test(orders): add API tests for create endpoint"
```

---

### Task 8: Order API Tests - List Endpoints

**Files:**

- Modify: `tests/modules/orders/test_order_api.py`

- [ ] **Step 1: Add TestOrderAPIList class**

```python
@pytest.mark.asyncio
class TestOrderAPIList:
    """Tests for GET /api/v1/orders endpoint."""
```

- [ ] **Step 2: Add test_get_orders_admin_success**

```python
    async def test_get_orders_admin_success(self, client, superuser_headers, test_order):
        """Test admin can list all orders."""
        response = await client.get("/api/v1/orders", headers=superuser_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert data["success"] is True
```

- [ ] **Step 3: Add test_get_orders_pagination**

```python
    async def test_get_orders_pagination(self, client, superuser_headers, test_order):
        """Test order listing with pagination."""
        response = await client.get(
            "/api/v1/orders?page=1&page_size=10",
            headers=superuser_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
```

- [ ] **Step 4: Add test_get_orders_filter_by_user**

```python
    async def test_get_orders_filter_by_user(self, client, superuser_headers, test_order):
        """Test filtering orders by user_id."""
        response = await client.get(
            f"/api/v1/orders?user_id={test_order.user_id}",
            headers=superuser_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) >= 1
```

- [ ] **Step 5: Add test_get_orders_unauthorized**

```python
    async def test_get_orders_unauthorized(self, client):
        """Test listing orders without authentication."""
        response = await client.get("/api/v1/orders")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

- [ ] **Step 6: Add test_get_orders_forbidden**

```python
    async def test_get_orders_forbidden(self, client, user_headers):
        """Test non-admin cannot list all orders."""
        response = await client.get("/api/v1/orders", headers=user_headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN
```

- [ ] **Step 7: Run tests**
Run: `uv run pytest tests/modules/orders/test_order_api.py::TestOrderAPIList -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add tests/modules/orders/test_order_api.py
git commit -m "test(orders): add API tests for list endpoint"
```

---

### Task 9: Order API Tests - My Orders Endpoint

**Files:**

- Modify: `tests/modules/orders/test_order_api.py`

- [ ] **Step 1: Add TestOrderAPIMyOrders class**

```python
@pytest.mark.asyncio
class TestOrderAPIMyOrders:
    """Tests for GET /api/v1/orders/my endpoint."""
```

- [ ] **Step 2: Add test_get_my_orders_success**

```python
    async def test_get_my_orders_success(self, client, user_headers, test_order):
        """Test getting current user's orders."""
        response = await client.get("/api/v1/orders/my", headers=user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["success"] is True
```

- [ ] **Step 3: Add test_get_my_orders_unauthorized**

```python
    async def test_get_my_orders_unauthorized(self, client):
        """Test getting my orders without authentication."""
        response = await client.get("/api/v1/orders/my")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

- [ ] **Step 4: Run tests**
Run: `uv run pytest tests/modules/orders/test_order_api.py::TestOrderAPIMyOrders -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/modules/orders/test_order_api.py
git commit -m "test(orders): add API tests for my orders endpoint"
```

---

### Task 10: Order API Tests - Get/Update/Delete Endpoints

**Files:**

- Modify: `tests/modules/orders/test_order_api.py`

- [ ] **Step 1: Add TestOrderAPIGetById class**

```python
@pytest.mark.asyncio
class TestOrderAPIGetById:
    """Tests for GET /api/v1/orders/{order_id} endpoint."""
```

- [ ] **Step 2: Add tests for get by ID**

```python
    async def test_get_order_by_id_found(self, client, user_headers, test_order):
        """Test getting order by ID."""
        response = await client.get(
            f"/api/v1/orders/{test_order.id}",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == test_order.id
        assert "items" in data["data"]

    async def test_get_order_by_id_not_found(self, client, user_headers):
        """Test getting non-existent order."""
        response = await client.get("/api/v1/orders/99999", headers=user_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_order_by_id_unauthorized(self, client, test_order):
        """Test getting order without authentication."""
        response = await client.get(f"/api/v1/orders/{test_order.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

- [ ] **Step 3: Add TestOrderAPIUpdate class**

```python
@pytest.mark.asyncio
class TestOrderAPIUpdate:
    """Tests for PUT /api/v1/orders/{order_id} endpoint."""
```

- [ ] **Step 4: Add tests for update**

```python
    async def test_update_order_status_admin_success(self, client, superuser_headers, test_order):
        """Test admin can update order status."""
        response = await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "CONFIRMED"},
            headers=superuser_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["status"] == "CONFIRMED"

    async def test_update_order_status_invalid_transition(self, client, superuser_headers, test_order):
        """Test invalid status transition."""
        response = await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "SHIPPED"},
            headers=superuser_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_update_order_forbidden(self, client, user_headers, test_order):
        """Test non-admin cannot update order."""
        response = await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "CONFIRMED"},
            headers=user_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_order_unauthorized(self, client, test_order):
        """Test updating order without authentication."""
        response = await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "CONFIRMED"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

- [ ] **Step 5: Add TestOrderAPIDelete class**

```python
@pytest.mark.asyncio
class TestOrderAPIDelete:
    """Tests for DELETE /api/v1/orders/{order_id} endpoint."""
```

- [ ] **Step 6: Add tests for delete**

```python
    async def test_delete_order_admin_success(self, client, superuser_headers, test_user, test_product_for_order):
        """Test admin can delete order."""
        from app.modules.orders.schemas import OrderCreate, OrderItemCreate
        from app.modules.orders import service as order_service

        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(
                    product_id=test_product_for_order.id,
                    quantity=1,
                    unit_price=Decimal("10.00")
                )
            ]
        )
        order = await order_service.create_order(superuser_headers.get("session", None) or client._session, order_in)

        response = await client.delete(
            f"/api/v1/orders/{order.id}",
            headers=superuser_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_order_forbidden(self, client, user_headers, test_order):
        """Test non-admin cannot delete order."""
        response = await client.delete(
            f"/api/v1/orders/{test_order.id}",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_order_unauthorized(self, client, test_order):
        """Test deleting order without authentication."""
        response = await client.delete(f"/api/v1/orders/{test_order.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

- [ ] **Step 7: Run all order API tests**
Run: `uv run pytest tests/modules/orders/test_order_api.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add tests/modules/orders/test_order_api.py
git commit -m "test(orders): complete API tests for get/update/delete endpoints"
```

---

## Module 2: Products Tests

### Task 11: Products Module Setup

**Files:**

- Create: `tests/modules/products/__init__.py`
- Create: `tests/modules/products/conftest.py`

- [ ] **Step 1: Create products test directory**

```bash
mkdir -p tests/modules/products
touch tests/modules/products/__init__.py
```

- [ ] **Step 2: Create products conftest.py**

```python
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio

from app.modules.products.schemas import ProductCreate
from app.modules.products import service as product_service


@pytest_asyncio.fixture
async def test_product(session):
    """Create a test product."""
    product_in = ProductCreate(
        name=f"Test Product {uuid.uuid4().hex[:8]}",
        sku=f"TEST-{uuid.uuid4().hex[:8]}",
        price=Decimal("49.99"),
        category="test"
    )
    return await product_service.create_product(session, product_in)


@pytest_asyncio.fixture
async def multiple_products(session):
    """Create multiple products for pagination tests."""
    products = []
    for i in range(5):
        product_in = ProductCreate(
            name=f"Product {i}",
            sku=f"SKU-{uuid.uuid4().hex[:8]}-{i}",
            price=Decimal(f"{10 + i}.99"),
            category="test" if i < 3 else "other"
        )
        products.append(await product_service.create_product(session, product_in))
    return products


@pytest_asyncio.fixture
async def superuser_headers(superuser_token):
    """Headers for admin API calls."""
    return {"Authorization": f"Bearer {superuser_token}"}


@pytest_asyncio.fixture
async def user_headers(user_token):
    """Headers for regular user API calls."""
    return {"Authorization": f"Bearer {user_token}"}
```

- [ ] **Step 3: Commit**

```bash
git add tests/modules/products/__init__.py tests/modules/products/conftest.py
git commit -m "test(products): add test fixtures for products module"
```

---

### Task 12: Product Service Tests - Create Operations

**Files:**

- Create: `tests/modules/products/test_product_service.py`

- [ ] **Step 1: Create test file with class**

```python
import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import ConflictException
from app.modules.products import service as product_service
from app.modules.products.schemas import ProductCreate, ProductUpdate


@pytest.mark.asyncio
class TestProductServiceCreate:
    """Tests for product creation."""
```

- [ ] **Step 2: Add test_create_product_success**

```python
    async def test_create_product_success(self, session):
        """Test successful product creation."""
        product_in = ProductCreate(
            name=f"Test Product {uuid.uuid4().hex[:8]}",
            sku=f"TEST-{uuid.uuid4().hex[:8]}",
            price=Decimal("99.99"),
            category="test"
        )
        product = await product_service.create_product(session, product_in)

        assert product.id is not None
        assert product.name == product_in.name
        assert product.sku == product_in.sku
        assert product.price == product_in.price
```

- [ ] **Step 3: Add test_create_product_duplicate_sku**

```python
    async def test_create_product_duplicate_sku(self, session):
        """Test creating product with duplicate SKU fails."""
        sku = f"TEST-{uuid.uuid4().hex[:8]}"

        product_in = ProductCreate(
            name="First Product",
            sku=sku,
            price=Decimal("99.99")
        )
        await product_service.create_product(session, product_in)

        duplicate = ProductCreate(
            name="Second Product",
            sku=sku,
            price=Decimal("49.99")
        )

        with pytest.raises(ConflictException) as exc_info:
            await product_service.create_product(session, duplicate)
        assert "already exists" in str(exc_info.value)
```

- [ ] **Step 4: Add test_create_product_negative_price**

```python
    async def test_create_product_negative_price(self, session):
        """Test creating product with negative price fails."""
        product_in = ProductCreate(
            name="Test Product",
            sku=f"TEST-{uuid.uuid4().hex[:8]}",
            price=Decimal("-10.00")
        )

        with pytest.raises(Exception):  # Pydantic validation error
            await product_service.create_product(session, product_in)
```

- [ ] **Step 5: Run tests**
Run: `uv run pytest tests/modules/products/test_product_service.py::TestProductServiceCreate -v`
Expected: Tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/modules/products/test_product_service.py
git commit -m "test(products): add service tests for product creation"
```

---

### Task 13: Product Service Tests - Get Operations

**Files:**

- Modify: `tests/modules/products/test_product_service.py`

- [ ] **Step 1: Add TestProductServiceGet class**

```python
@pytest.mark.asyncio
class TestProductServiceGet:
    """Tests for product retrieval."""
```

- [ ] **Step 2: Add tests**

```python
    async def test_get_product_by_id_found(self, session, test_product):
        """Test getting product by ID when it exists."""
        product = await product_service.get_product_by_id(session, test_product.id)

        assert product is not None
        assert product.id == test_product.id

    async def test_get_product_by_id_not_found(self, session):
        """Test getting product by ID when it doesn't exist."""
        product = await product_service.get_product_by_id(session, 99999)

        assert product is None

    async def test_get_product_by_sku_found(self, session, test_product):
        """Test getting product by SKU when it exists."""
        product = await product_service.get_product_by_sku(session, test_product.sku)

        assert product is not None
        assert product.sku == test_product.sku

    async def test_get_product_by_sku_not_found(self, session):
        """Test getting product by SKU when it doesn't exist."""
        product = await product_service.get_product_by_sku(session, "NONEXISTENT")

        assert product is None
```

- [ ] **Step 3: Run tests**
Run: `uv run pytest tests/modules/products/test_product_service.py::TestProductServiceGet -v`
Expected: Tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/modules/products/test_product_service.py
git commit -m "test(products): add service tests for product retrieval"
```

---

### Task 14: Product Service Tests - List Operations

**Files:**

- Modify: `tests/modules/products/test_product_service.py`

- [ ] **Step 1: Add TestProductServiceList class**

```python
@pytest.mark.asyncio
class TestProductServiceList:
    """Tests for product listing."""
```

- [ ] **Step 2: Add tests**

```python
    async def test_get_products_pagination(self, session, multiple_products):
        """Test product listing with pagination."""
        page1 = await product_service.get_products(session, skip=0, limit=2)
        page2 = await product_service.get_products(session, skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2

    async def test_get_products_by_category(self, session, multiple_products):
        """Test filtering products by category."""
        test_products = await product_service.get_products_by_category(session, "test")

        assert len(test_products) >= 3
        assert all(p.category == "test" for p in test_products)

    async def test_get_products_count(self, session, multiple_products):
        """Test product count."""
        count = await product_service.get_products_count(session)
        assert count >= 5
```

- [ ] **Step 3: Run tests**
Run: `uv run pytest tests/modules/products/test_product_service.py::TestProductServiceList -v`
Expected: Tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/modules/products/test_product_service.py
git commit -m "test(products): add service tests for product listing"
```

---

### Task 15: Product Service Tests - Update/Delete Operations

**Files:**

- Modify: `tests/modules/products/test_product_service.py`

- [ ] **Step 1: Add TestProductServiceUpdate class**

```python
@pytest.mark.asyncio
class TestProductServiceUpdate:
    """Tests for product update."""
```

- [ ] **Step 2: Add tests**

```python
    async def test_update_product_success(self, session, test_product):
        """Test successful product update."""
        update = ProductUpdate(
            name="Updated Name",
            price=Decimal("79.99")
        )
        product = await product_service.update_product(session, test_product.id, update)

        assert product.name == "Updated Name"
        assert product.price == Decimal("79.99")

    async def test_update_product_partial(self, session, test_product):
        """Test partial product update."""
        update = ProductUpdate(name="New Name")
        product = await product_service.update_product(session, test_product.id, update)

        assert product.name == "New Name"
        assert product.price == test_product.price  # Unchanged

    async def test_update_product_not_found(self, session):
        """Test updating non-existent product."""
        update = ProductUpdate(name="New Name")

        with pytest.raises(Exception) as exc_info:
            await product_service.update_product(session, 99999, update)
        assert "not found" in str(exc_info.value)
```

- [ ] **Step 3: Add TestProductServiceDelete class**

```python
@pytest.mark.asyncio
class TestProductServiceDelete:
    """Tests for product deletion."""
```

- [ ] **Step 4: Add tests**

```python
    async def test_delete_product_found(self, session, test_product):
        """Test deleting existing product."""
        deleted = await product_service.delete_product(session, test_product.id)

        assert deleted.id == test_product.id

        result = await product_service.get_product_by_id(session, test_product.id)
        assert result is None

    async def test_delete_product_not_found(self, session):
        """Test deleting non-existent product."""
        with pytest.raises(Exception) as exc_info:
            await product_service.delete_product(session, 99999)
        assert "not found" in str(exc_info.value)
```

- [ ] **Step 5: Run all product service tests**
Run: `uv run pytest tests/modules/products/test_product_service.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/modules/products/test_product_service.py
git commit -m "test(products): complete service tests for update/delete"
```

---

### Task 16: Product API Tests

**Files:**

- Create: `tests/modules/products/test_product_api.py`

- [ ] **Step 1: Create test file with imports**

```python
import uuid
from decimal import Decimal

import pytest
from fastapi import status


@pytest.mark.asyncio
class TestProductAPICreate:
    """Tests for POST /api/v1/products endpoint."""
```

- [ ] **Step 2: Add create tests**

```python
    async def test_create_product_admin_success(self, client, superuser_headers):
        """Test admin can create product."""
        response = await client.post(
            "/api/v1/products",
            json={
                "name": f"Test Product {uuid.uuid4().hex[:8]}",
                "sku": f"TEST-{uuid.uuid4().hex[:8]}",
                "price": "99.99",
                "category": "test"
            },
            headers=superuser_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True

    async def test_create_product_forbidden(self, client, user_headers):
        """Test non-admin cannot create product."""
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Test",
                "sku": f"TEST-{uuid.uuid4().hex[:8]}",
                "price": "99.99"
            },
            headers=user_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_create_product_unauthorized(self, client):
        """Test creating product without auth."""
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Test",
                "sku": "TEST",
                "price": "99.99"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

- [ ] **Step 3: Add TestProductAPIList class**

```python
@pytest.mark.asyncio
class TestProductAPIList:
    """Tests for GET /api/v1/products endpoint."""
```

- [ ] **Step 4: Add list tests**

```python
    async def test_get_products_authenticated_success(self, client, user_headers, test_product):
        """Test authenticated user can list products."""
        response = await client.get("/api/v1/products", headers=user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data

    async def test_get_products_filter_by_category(self, client, user_headers, multiple_products):
        """Test filtering products by category."""
        response = await client.get(
            "/api/v1/products?category=test",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_get_products_unauthorized(self, client):
        """Test listing products without auth."""
        response = await client.get("/api/v1/products")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

- [ ] **Step 5: Add TestProductAPIGetById class**

```python
@pytest.mark.asyncio
class TestProductAPIGetById:
    """Tests for GET /api/v1/products/{product_id} and /sku/{sku} endpoints."""
```

- [ ] **Step 6: Add get by ID tests**

```python
    async def test_get_product_by_id_found(self, client, user_headers, test_product):
        """Test getting product by ID."""
        response = await client.get(
            f"/api/v1/products/{test_product.id}",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == test_product.id

    async def test_get_product_by_id_not_found(self, client, user_headers):
        """Test getting non-existent product."""
        response = await client.get("/api/v1/products/99999", headers=user_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_product_by_sku_found(self, client, user_headers, test_product):
        """Test getting product by SKU."""
        response = await client.get(
            f"/api/v1/products/sku/{test_product.sku}",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_get_product_by_sku_not_found(self, client, user_headers):
        """Test getting non-existent product by SKU."""
        response = await client.get("/api/v1/products/sku/NONEXISTENT", headers=user_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
```

- [ ] **Step 7: Add TestProductAPIUpdate and TestProductAPIDelete classes**

```python
@pytest.mark.asyncio
class TestProductAPIUpdate:
    """Tests for PUT /api/v1/products/{product_id} endpoint."""

    async def test_update_product_admin_success(self, client, superuser_headers, test_product):
        """Test admin can update product."""
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            json={"name": "Updated Name"},
            headers=superuser_headers
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_update_product_forbidden(self, client, user_headers, test_product):
        """Test non-admin cannot update product."""
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            json={"name": "Updated"},
            headers=user_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestProductAPIDelete:
    """Tests for DELETE /api/v1/products/{product_id} endpoint."""

    async def test_delete_product_admin_success(self, client, superuser_headers, test_product):
        """Test admin can delete product."""
        response = await client.delete(
            f"/api/v1/products/{test_product.id}",
            headers=superuser_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_product_forbidden(self, client, user_headers, test_product):
        """Test non-admin cannot delete product."""
        response = await client.delete(
            f"/api/v1/products/{test_product.id}",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
```

- [ ] **Step 8: Run all product API tests**
Run: `uv run pytest tests/modules/products/test_product_api.py -v`
Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
git add tests/modules/products/test_product_api.py
git commit -m "test(products): add comprehensive API tests"
```

---

## Module 3: Audit Tests

### Task 17: Audit Module Setup

**Files:**

- Create: `tests/modules/audit/__init__.py`
- Create: `tests/modules/audit/conftest.py`

- [ ] **Step 1: Create audit test directory**

```bash
mkdir -p tests/modules/audit
touch tests/modules/audit/__init__.py
```

- [ ] **Step 2: Create audit conftest.py**

```python
import pytest
import pytest_asyncio

from app.modules.audit.schemas import AuditLogCreate
from app.modules.audit import service as audit_service


@pytest_asyncio.fixture
async def test_audit_log(session, test_user):
    """Create a test audit log."""
    log_in = AuditLogCreate(
        user_id=test_user.id,
        action="CREATE",
        resource_type="order",
        resource_id=1,
        old_value=None,
        new_value='{"id": 1, "status": "PENDING"}',
        ip_address="127.0.0.1"
    )
    return await audit_service.create_audit_log(session, log_in)


@pytest_asyncio.fixture
async def multiple_audit_logs(session, test_user):
    """Create multiple audit logs for pagination tests."""
    from app.modules.audit.schemas import AuditLogCreate
    from app.modules.audit import service as audit_service

    logs = []
    for i in range(5):
        log_in = AuditLogCreate(
            user_id=test_user.id,
            action=["CREATE", "UPDATE", "DELETE"][i % 3],
            resource_type="order",
            resource_id=i + 1
        )
        logs.append(await audit_service.create_audit_log(session, log_in))
    return logs


@pytest_asyncio.fixture
async def superuser_headers(superuser_token):
    """Headers for admin API calls."""
    return {"Authorization": f"Bearer {superuser_token}"}


@pytest_asyncio.fixture
async def user_headers(user_token):
    """Headers for regular user API calls."""
    return {"Authorization": f"Bearer {user_token}"}
```

- [ ] **Step 3: Commit**

```bash
git add tests/modules/audit/__init__.py tests/modules/audit/conftest.py
git commit -m "test(audit): add test fixtures for audit module"
```

---

### Task 18: Audit Service Tests

**Files:**

- Create: `tests/modules/audit/test_audit_service.py`

- [ ] **Step 1: Create test file**

```python
import pytest

from app.modules.audit import service as audit_service
from app.modules.audit.schemas import AuditLogCreate


@pytest.mark.asyncio
class TestAuditServiceCreate:
    """Tests for audit log creation."""

    async def test_create_audit_log_success(self, session, test_user):
        """Test successful audit log creation."""
        log_in = AuditLogCreate(
            user_id=test_user.id,
            action="CREATE",
            resource_type="order",
            resource_id=1,
            new_value='{"status": "PENDING"}',
            ip_address="127.0.0.1"
        )
        log = await audit_service.create_audit_log(session, log_in)

        assert log.id is not None
        assert log.user_id == test_user.id
        assert log.action == "CREATE"

    async def test_create_audit_log_without_user_id(self, session):
        """Test audit log without user_id (system action)."""
        log_in = AuditLogCreate(
            user_id=None,
            action="SYSTEM",
            resource_type="task",
            resource_id=1
        )
        log = await audit_service.create_audit_log(session, log_in)

        assert log.user_id is None

    async def test_create_audit_log_minimal(self, session):
        """Test audit log with minimal fields."""
        log_in = AuditLogCreate(
            action="VIEW",
            resource_type="product",
            resource_id=1
        )
        log = await audit_service.create_audit_log(session, log_in)

        assert log.action == "VIEW"


@pytest.mark.asyncio
class TestAuditServiceGet:
    """Tests for audit log retrieval."""

    async def test_get_audit_log_by_id_found(self, session, test_audit_log):
        """Test getting audit log by ID."""
        log = await audit_service.get_audit_log_by_id(session, test_audit_log.id)

        assert log is not None
        assert log.id == test_audit_log.id

    async def test_get_audit_log_by_id_not_found(self, session):
        """Test getting non-existent audit log."""
        log = await audit_service.get_audit_log_by_id(session, 99999)

        assert log is None


@pytest.mark.asyncio
class TestAuditServiceList:
    """Tests for audit log listing."""

    async def test_get_audit_logs_pagination(self, session, multiple_audit_logs):
        """Test audit log listing with pagination."""
        page1 = await audit_service.get_audit_logs(session, skip=0, limit=2)

        assert len(page1) == 2

    async def test_get_audit_logs_by_user(self, session, test_user, multiple_audit_logs):
        """Test filtering audit logs by user."""
        logs = await audit_service.get_audit_logs_by_user(session, test_user.id)

        assert len(logs) >= 5

    async def test_get_audit_logs_by_resource(self, session, multiple_audit_logs):
        """Test filtering audit logs by resource."""
        logs = await audit_service.get_audit_logs_by_resource(session, "order", 1)

        assert all(l.resource_type == "order" and l.resource_id == 1 for l in logs)

    async def test_get_audit_logs_count(self, session, multiple_audit_logs):
        """Test audit log count."""
        count = await audit_service.get_audit_logs_count(session)
        assert count >= 5
```

- [ ] **Step 2: Run tests**
Run: `uv run pytest tests/modules/audit/test_audit_service.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/modules/audit/test_audit_service.py
git commit -m "test(audit): add comprehensive service tests"
```

---

### Task 19: Audit API Tests

**Files:**

- Create: `tests/modules/audit/test_audit_api.py`

- [ ] **Step 1: Create test file**

```python
import pytest
from fastapi import status


@pytest.mark.asyncio
class TestAuditAPIList:
    """Tests for GET /api/v1/audit endpoint."""

    async def test_get_audit_logs_admin_success(self, client, superuser_headers, test_audit_log):
        """Test admin can list audit logs."""
        response = await client.get("/api/v1/audit", headers=superuser_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data

    async def test_get_audit_logs_filter_by_user(self, client, superuser_headers, test_audit_log):
        """Test filtering audit logs by user_id."""
        response = await client.get(
            f"/api/v1/audit?user_id={test_audit_log.user_id}",
            headers=superuser_headers
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_get_audit_logs_filter_by_resource(self, client, superuser_headers, test_audit_log):
        """Test filtering audit logs by resource."""
        response = await client.get(
            f"/api/v1/audit?resource_type=order&resource_id={test_audit_log.resource_id}",
            headers=superuser_headers
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_get_audit_logs_unauthorized(self, client):
        """Test listing audit logs without auth."""
        response = await client.get("/api/v1/audit")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_audit_logs_forbidden(self, client, user_headers):
        """Test non-admin cannot list audit logs."""
        response = await client.get("/api/v1/audit", headers=user_headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestAuditAPIGetById:
    """Tests for GET /api/v1/audit/{log_id} endpoint."""

    async def test_get_audit_log_by_id_admin_success(self, client, superuser_headers, test_audit_log):
        """Test admin can get audit log by ID."""
        response = await client.get(
            f"/api/v1/audit/{test_audit_log.id}",
            headers=superuser_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == test_audit_log.id

    async def test_get_audit_log_by_id_not_found(self, client, superuser_headers):
        """Test getting non-existent audit log."""
        response = await client.get("/api/v1/audit/99999", headers=superuser_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_audit_log_by_id_unauthorized(self, client, test_audit_log):
        """Test getting audit log without auth."""
        response = await client.get(f"/api/v1/audit/{test_audit_log.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_audit_log_by_id_forbidden(self, client, user_headers, test_audit_log):
        """Test non-admin cannot get audit log."""
        response = await client.get(
            f"/api/v1/audit/{test_audit_log.id}",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
```

- [ ] **Step 2: Run tests**
Run: `uv run pytest tests/modules/audit/test_audit_api.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/modules/audit/test_audit_api.py
git commit -m "test(audit): add comprehensive API tests"
```

---

## Final Verification

### Task 20: Run All Tests and Verify Coverage

- [ ] **Step 1: Run all new tests**
Run: `uv run pytest tests/modules/orders tests/modules/products tests/modules/audit -v`
Expected: All tests PASS

- [ ] **Step 2: Run full test suite**
Run: `uv run pytest tests -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 3: Run with coverage**
Run: `uv run pytest tests/modules/orders tests/modules/products tests/modules/audit --cov=app/modules/orders --cov=app/modules/products --cov=app/modules/audit --cov-report=term-missing`
Expected: 90%+ coverage on service layers

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "test: complete comprehensive test coverage for orders, products, and audit modules"
```

---

## Summary

**Total Test Cases:** 110+

- Orders: ~45 tests (25 service + 20 API)
- Products: ~38 tests (20 service + 18 API)
- Audit: ~27 tests (15 service + 12 API)

**Files Created:** 12 files

- 3 `__init__.py`
- 3 `conftest.py`
- 3 `test_*_service.py`
- 3 `test_*_api.py`

**Commits:** ~20 incremental commits following TDD pattern
