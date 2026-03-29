# Test Code Refactoring Design

## Overview

Full structural rewrite of all test files to eliminate duplication, improve patterns, and standardize conventions across the project.

## Problem Statement

Current test code has several issues:

1. **Duplicated fixtures**: `superuser_headers`, `user_headers` are identical in 3 conftest files
2. **Heavy boilerplate**: Order service tests repeat `patch("app.modules.orders.service.dispatch") + OrderCreate` pattern 8+ times
3. **Bad import practices**: `import uuid` inside every test method in roles tests (7+ times)
4. **Fragile pagination tests**: Some tests rely on data from other tests
5. **Unused imports**: `MagicMock`, `patch` imported but unused
6. **Inconsistent assertions**: `status in [400, 422]` vs specific code
7. **No parametrize usage**: Status transition tests should use parametrize

## Design

### Section 1: Root conftest.py Restructuring

Move shared fixtures to `tests/conftest.py`:

```python
@pytest_asyncio.fixture
async def superuser_headers(superuser_token):
    return {"Authorization": f"Bearer {superuser_token}"}

@pytest_asyncio.fixture
async def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}
```

Delete duplicated `superuser_headers`, `user_headers` from:

- `tests/modules/orders/conftest.py`
- `tests/modules/products/conftest.py`
- `tests/modules/audit/conftest.py`

### Section 2: Orders Tests - Eliminate Boilerplate

**New fixtures (orders/conftest.py):**

```python
@pytest_asyncio.fixture
def patch_dispatch():
    """Mock the Celery dispatch to avoid real task execution."""
    with patch("app.modules.orders.service.dispatch"):
        yield

@pytest_asyncio.fixture
async def fresh_order(session, test_user, test_product_for_order, patch_dispatch):
    """Create a fresh PENDING order for each test."""
    return await order_service.create_order(session, OrderCreate(
        user_id=test_user.id,
        items=[OrderItemCreate(
            product_id=test_product_for_order.id,
            quantity=1,
            unit_price=Decimal("10.00")
        )]
    ))
```

**Status transitions with parametrize:**

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("before,after", [
    (OrderStatus.PENDING, OrderStatus.CONFIRMED),
    (OrderStatus.PENDING, OrderStatus.CANCELLED),
    (OrderStatus.CONFIRMED, OrderStatus.SHIPPED),
    (OrderStatus.CONFIRMED, OrderStatus.CANCELLED),
    (OrderStatus.SHIPPED, OrderStatus.COMPLETED),
])
class TestOrderServiceValidTransitions:
    async def test_valid_transition(self, session, fresh_order, before, after):
        if fresh_order.status != before.value:
            fresh_order.status = before.value
            await session.commit()
        updated = await order_service.update_order_status(
            session, fresh_order.id, OrderUpdate(status=after)
        )
        assert updated.status == after.value

@pytest.mark.asyncio
@pytest.mark.parametrize("before,invalid", [
    (OrderStatus.COMPLETED, OrderStatus.CANCELLED),
    (OrderStatus.COMPLETED, OrderStatus.PENDING),
    (OrderStatus.CANCELLED, OrderStatus.CONFIRMED),
    (OrderStatus.PENDING, OrderStatus.SHIPPED),
])
class TestOrderServiceInvalidTransitions:
    async def test_invalid_transition(self, session, fresh_order, before, invalid):
        if fresh_order.status != before.value:
            fresh_order.status = before.value
            await session.commit()
        with pytest.raises(ValidationException):
            await order_service.update_order_status(
                session, fresh_order.id, OrderUpdate(status=invalid)
            )
```

### Section 3: Roles Tests - Fix import uuid

Move `import uuid` from inside test methods to file top level:

```python
import uuid  # File top level

@pytest.mark.asyncio
class TestRoleService:
    async def test_create_role_success(self, session):
        unique_id = str(uuid.uuid4())[:8]  # No import needed
```

Also fix: remove `import uuid` from inside test methods in `test_permission_service.py`.

### Section 4: Pagination Tests - Explicit Data Creation

Each pagination test creates its own data instead of relying on fixtures:

```python
async def test_list_orders_pagination(self, client, superuser_headers, session, test_user, test_product_for_order, patch_dispatch):
    for _ in range(3):
        await order_service.create_order(session, OrderCreate(
            user_id=test_user.id,
            items=[OrderItemCreate(product_id=test_product_for_order.id, quantity=1, unit_price=Decimal("10.00"))]
        ))
    response = await client.get("/api/v1/orders/?page=1&page_size=2", headers=superuser_headers)
    assert len(response.json()["data"]) == 2
```

### Section 5: Code Quality Improvements

- Remove unused imports: `MagicMock`, `patch` where not needed
- Use `session: AsyncSession` type hints consistently (like audit tests)
- Standardize assertions: specific status codes, not lists
- Standardize naming: `test_<action>_<condition>` pattern
- Remove redundant docstrings when test name is clear
- Clean up fixture naming: module-specific `test_<resource>`, shared no prefix

### Section 6: Test Helpers Module

Create `tests/helpers.py` for factory functions:

```python
import uuid
from decimal import Decimal

from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from app.modules.products.schemas import ProductCreate


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
```

## File Changes

**Execution order matters.** Steps 1-2 must complete before 3-5.

| #   | File                                             | Action                                                          |
| --- | ------------------------------------------------ | --------------------------------------------------------------- |
| 1   | `tests/conftest.py`                              | Add `superuser_headers`, `user_headers`                         |
| 2   | `tests/helpers.py`                               | Create factory functions                                        |
| 3   | `tests/modules/orders/conftest.py`               | Add `patch_dispatch`, `fresh_order`; remove duplicated fixtures |
| 4   | `tests/modules/orders/test_order_service.py`     | Rewrite with fixture usage, parametrize                         |
| 5   | `tests/modules/orders/test_order_api.py`         | Rewrite with `patch_dispatch` fixture                           |
| 6   | `tests/modules/products/conftest.py`             | Remove duplicated fixtures                                      |
| 7   | `tests/modules/products/test_product_service.py` | Fix imports, use helpers                                        |
| 8   | `tests/modules/products/test_product_api.py`     | Fix status code assertions                                      |
| 9   | `tests/modules/audit/conftest.py`                | Remove duplicated fixtures                                      |
| 10  | `tests/modules/audit/test_audit_service.py`      | Add type hints                                                  |
| 11  | `tests/modules/audit/test_audit_api.py`          | Fix status code assertions                                      |
| 12  | `tests/modules/roles/test_role_service.py`       | Move `import uuid` to top                                       |
| 13  | `tests/modules/roles/test_permission_service.py` | Move `import uuid` to top                                       |

**Helper usage policy:** Use `tests/helpers.py` factories only where repetition exists (>2 times). Simple one-off tests use raw schemas directly. The goal is to eliminate boilerplate, not to abstract for abstraction's sake.

## Success Criteria

1. All 147 tests pass
2. No duplicated fixtures across conftest files
3. No `import uuid` inside test methods
4. All status transition tests use parametrize
5. No unused imports
6. All pagination tests create their own data
7. Consistent assertion patterns
