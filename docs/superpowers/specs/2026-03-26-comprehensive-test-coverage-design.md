# Comprehensive Test Coverage for Business-Critical Modules

## Metadata

- **Date**: 2026-03-26
- **Author**: AI Assistant
- **Status**: Draft
- **Target Modules**: Orders, Products, Audit
- **Test Types**: Service + API tests

## Overview

Add comprehensive test coverage for three business-critical modules that currently lack tests. The test suite will include service layer unit tests and API integration tests, following established patterns from existing user and role tests.

### Current State

**Existing Test Coverage:**

- ✅ Users module: API tests (auth, login, CRUD) - 481 lines
- ✅ Roles module: Service tests (roles & permissions) - 125 lines
- ✅ Tasks module: Service, API, dispatcher tests - recent addition

**Modules Without Tests:**

- ❌ Orders module: 0 tests
- ❌ Products module: 0 tests
- ❌ Audit module: 0 tests
- ❌ Config module: 0 tests
- ❌ Notifications module: 0 tests

### Priority

**Business-Critical First**: Orders → Products → Audit

1. **Orders**: Most complex business logic (status transitions, timeout cancellation, total calculation)
2. **Products**: Critical uniqueness constraints (SKU validation), essential for order creation
3. **Audit**: Essential for compliance and debugging, read-only operations

Config and Notifications modules will be addressed in a future iteration.

## Architecture

### Test Structure

```text
tests/modules/
├── orders/
│   ├── __init__.py
│   ├── conftest.py              # Order-specific fixtures
│   ├── test_order_service.py    # Service layer unit tests
│   └── test_order_api.py        # API integration tests
├── products/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_product_service.py
│   └── test_product_api.py
└── audit/
    ├── __init__.py
    ├── conftest.py
    ├── test_audit_service.py
    └── test_audit_api.py
```

### Test Layering

**Service Tests** (Unit Level):

- Test business logic in isolation
- Use in-memory SQLite database
- Test return values, exceptions, state changes
- Mock external dependencies (Celery tasks)

**API Tests** (Integration Level):

- Test complete request-to-response flow
- Test authentication and authorization
- Test request validation and error responses
- Test response structure and status codes

### Existing Infrastructure

Tests will leverage existing fixtures from `tests/conftest.py`:

- `setup_test_db`: Creates in-memory SQLite database
- `session`: AsyncSession with auto-rollback
- `client`: Async HTTP client
- `test_user`: Creates a test user
- `user_token`: JWT token for regular user
- `superuser_token`: JWT token for admin user

## Module 1: Orders Tests

### Business Logic Under Test

**Order Service (`app/modules/orders/service.py`):**

- `create_order`: Creates order with items, calculates total, dispatches timeout task
- `update_order_status`: Validates and updates status with state machine rules
- `get_order_by_id`, `get_order_with_items`, `get_orders`, `get_orders_by_user`, `get_orders_by_status`: Retrieval operations
- `delete_order`: Soft delete

**Status State Machine:**

```text
PENDING → CONFIRMED → SHIPPED → COMPLETED
   ↓         ↓
CANCELLED  CANCELLED

Valid transitions:
- PENDING → CONFIRMED, CANCELLED
- CONFIRMED → SHIPPED, CANCELLED
- SHIPPED → COMPLETED
- COMPLETED → (terminal)
- CANCELLED → (terminal)
```

### Service Test Cases (~25 tests)

**Create Order:**

- `test_create_order_success`: Happy path with multiple items
- `test_create_order_single_item`: Order with one item
- `test_create_order_empty_items`: Validation error for empty items list
- `test_create_order_total_calculation`: Verify total amount calculation
- `test_create_order_zero_quantity`: Validation error (quantity > 0)
- `test_create_order_negative_quantity`: Validation error
- `test_create_order_zero_price`: Validation error (unit_price > 0)
- `test_create_order_negative_price`: Validation error
- `test_create_order_dispatches_timeout_task`: Verify Celery task dispatch

**Get Order:**

- `test_get_order_by_id_found`: Returns order
- `test_get_order_by_id_not_found`: Returns None
- `test_get_order_with_items_found`: Returns order with loaded items
- `test_get_order_with_items_not_found`: Returns None

**List Orders:**

- `test_get_orders_pagination`: Verify skip/limit
- `test_get_orders_by_user`: Filter by user_id
- `test_get_orders_by_status`: Filter by status (each status type)
- `test_get_orders_count`: Verify count function

**Update Order Status:**

- `test_update_status_pending_to_confirmed`: Valid transition
- `test_update_status_pending_to_cancelled`: Valid transition
- `test_update_status_confirmed_to_shipped`: Valid transition
- `test_update_status_confirmed_to_cancelled`: Valid transition
- `test_update_status_shipped_to_completed`: Valid transition
- `test_update_status_completed_to_any`: Invalid transition
- `test_update_status_cancelled_to_any`: Invalid transition
- `test_update_status_pending_to_shipped`: Invalid transition (skip)
- `test_update_status_order_not_found`: NotFoundException

**Delete Order:**

- `test_delete_order_found`: Success
- `test_delete_order_not_found`: NotFoundException

### API Test Cases (~20 tests)

**POST /api/v1/orders:**

- `test_create_order_success`: 201 with created order
- `test_create_order_unauthorized`: 401 without token
- `test_create_order_empty_items`: 422 validation error
- `test_create_order_invalid_quantity`: 422 for quantity <= 0
- `test_create_order_invalid_price`: 422 for unit_price <= 0

**GET /api/v1/orders (Admin):**

- `test_get_orders_admin_success`: 200 with paginated orders
- `test_get_orders_pagination`: Verify page/page_size params
- `test_get_orders_filter_by_user`: Filter by user_id query param
- `test_get_orders_filter_by_status`: Filter by status query param
- `test_get_orders_unauthorized`: 401 without token
- `test_get_orders_forbidden`: 403 for non-admin

**GET /api/v1/orders/my:**

- `test_get_my_orders_success`: 200 with user's own orders
- `test_get_my_orders_unauthorized`: 401 without token

**GET /api/v1/orders/{order_id}:**

- `test_get_order_by_id_found`: 200 with order details
- `test_get_order_by_id_not_found`: 404
- `test_get_order_by_id_unauthorized`: 401

**PUT /api/v1/orders/{order_id}:**

- `test_update_order_status_admin_success`: 200 for admin
- `test_update_order_status_invalid_transition`: 422 for invalid transition
- `test_update_order_status_not_found`: 404
- `test_update_order_status_unauthorized`: 401
- `test_update_order_status_forbidden`: 403 for non-admin

**DELETE /api/v1/orders/{order_id}:**

- `test_delete_order_admin_success`: 204
- `test_delete_order_not_found`: 404
- `test_delete_order_unauthorized`: 401
- `test_delete_order_forbidden`: 403 for non-admin

## Module 2: Products Tests

### Business Logic Under Test

**Product Service (`app/modules/products/service.py`):**

- `create_product`: Creates product with SKU uniqueness check
- `get_product_by_id`, `get_product_by_sku`: Retrieval operations
- `get_products`, `get_products_by_category`: Listing with filtering
- `update_product`: Update product fields
- `delete_product`: Soft delete

**Key Constraints:**

- SKU must be unique across all products
- Price must be > 0
- Name, SKU have max length constraints
- Category is optional but has max length

### Service Test Cases (~20 tests)

**Create Product:**

- `test_create_product_success`: Happy path
- `test_create_product_duplicate_sku`: ConflictException
- `test_create_product_empty_name`: Validation (min_length=1)
- `test_create_product_empty_sku`: Validation (min_length=1)
- `test_create_product_negative_price`: Validation (price > 0)
- `test_create_product_zero_price`: Validation error
- `test_create_product_max_length_name`: Max length boundary
- `test_create_product_max_length_sku`: Max length boundary

**Get Product:**

- `test_get_product_by_id_found`: Returns product
- `test_get_product_by_id_not_found`: Returns None
- `test_get_product_by_sku_found`: Returns product
- `test_get_product_by_sku_not_found`: Returns None

**List Products:**

- `test_get_products_pagination`: Verify skip/limit
- `test_get_products_by_category`: Filter by category
- `test_get_products_count`: Verify count function

**Update Product:**

- `test_update_product_success`: Update all fields
- `test_update_product_partial`: Update only some fields
- `test_update_product_not_found`: NotFoundException
- `test_update_product_unchanged_sku`: No conflict if SKU unchanged

**Delete Product:**

- `test_delete_product_found`: Success
- `test_delete_product_not_found`: NotFoundException

### API Test Cases (~18 tests)

**POST /api/v1/products:**

- `test_create_product_admin_success`: 201 for admin
- `test_create_product_duplicate_sku`: 409 Conflict
- `test_create_product_unauthorized`: 401 without token
- `test_create_product_forbidden`: 403 for non-admin
- `test_create_product_invalid_price`: 422 for price <= 0
- `test_create_product_empty_name`: 422 validation error

**GET /api/v1/products:**

- `test_get_products_authenticated_success`: 200 for authenticated user
- `test_get_products_pagination`: Verify page/page_size params
- `test_get_products_filter_by_category`: Filter by category query param
- `test_get_products_unauthorized`: 401 without token

**GET /api/v1/products/sku/{sku}:**

- `test_get_product_by_sku_found`: 200 with product
- `test_get_product_by_sku_not_found`: 404
- `test_get_product_by_sku_unauthorized`: 401

**GET /api/v1/products/{product_id}:**

- `test_get_product_by_id_found`: 200 with product
- `test_get_product_by_id_not_found`: 404
- `test_get_product_by_id_unauthorized`: 401

**PUT /api/v1/products/{product_id}:**

- `test_update_product_admin_success`: 200 for admin
- `test_update_product_not_found`: 404
- `test_update_product_unauthorized`: 401
- `test_update_product_forbidden`: 403 for non-admin

**DELETE /api/v1/products/{product_id}:**

- `test_delete_product_admin_success`: 204
- `test_delete_product_not_found`: 404
- `test_delete_product_unauthorized`: 401
- `test_delete_product_forbidden`: 403 for non-admin

## Module 3: Audit Tests

### Business Logic Under Test

**Audit Service (`app/modules/audit/service.py`):**

- `create_audit_log`: Creates log entry (no uniqueness constraints)
- `get_audit_log_by_id`: Single log retrieval
- `get_audit_logs`: Paginated list
- `get_audit_logs_by_user`: Filter by user_id
- `get_audit_logs_by_resource`: Filter by resource_type + resource_id
- `get_audit_logs_count`: Total count

**Key Characteristics:**

- Audit logs are append-only (no update/delete)
- Admin-only read access
- Support filtering by user or resource

### Service Test Cases (~15 tests)

**Create Audit Log:**

- `test_create_audit_log_success`: Happy path with all fields
- `test_create_audit_log_without_user_id`: System action
- `test_create_audit_log_with_old_new_values`: Change tracking
- `test_create_audit_log_with_ip_address`: Request tracking
- `test_create_audit_log_minimal`: Only required fields

**Get Audit Log:**

- `test_get_audit_log_by_id_found`: Returns log
- `test_get_audit_log_by_id_not_found`: Returns None

**List Audit Logs:**

- `test_get_audit_logs_pagination`: Verify skip/limit
- `test_get_audit_logs_by_user`: Filter by user_id
- `test_get_audit_logs_by_user_pagination`: Pagination with filter
- `test_get_audit_logs_by_resource`: Filter by resource_type + resource_id
- `test_get_audit_logs_by_resource_pagination`: Pagination with filter
- `test_get_audit_logs_count`: Verify count function

### API Test Cases (~12 tests)

**GET /api/v1/audit:**

- `test_get_audit_logs_admin_success`: 200 for admin
- `test_get_audit_logs_pagination`: Verify page/page_size params
- `test_get_audit_logs_filter_by_user`: Filter by user_id query param
- `test_get_audit_logs_filter_by_resource`: Filter by resource_type + resource_id
- `test_get_audit_logs_unauthorized`: 401 without token
- `test_get_audit_logs_forbidden`: 403 for non-admin

**GET /api/v1/audit/{log_id}:**

- `test_get_audit_log_by_id_admin_success`: 200 for admin
- `test_get_audit_log_by_id_not_found`: 404
- `test_get_audit_log_by_id_unauthorized`: 401
- `test_get_audit_log_by_id_forbidden`: 403 for non-admin

## Test Fixtures

### Orders Module Fixtures (`tests/modules/orders/conftest.py`)

```python
@pytest_asyncio.fixture
async def test_product_for_order(session):
    """Create a product for order tests."""
    from app.modules.products.schemas import ProductCreate
    from app.modules.products import service as product_service

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
    from app.modules.orders.schemas import OrderCreate, OrderItemCreate
    from app.modules.orders import service as order_service

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
async def superuser_headers(client, superuser_token):
    """Headers for admin API calls."""
    return {"Authorization": f"Bearer {superuser_token}"}

@pytest_asyncio.fixture
async def user_headers(client, user_token):
    """Headers for regular user API calls."""
    return {"Authorization": f"Bearer {user_token}"}
```

### Products Module Fixtures (`tests/modules/products/conftest.py`)

```python
@pytest_asyncio.fixture
async def test_product(session):
    """Create a test product."""
    from app.modules.products.schemas import ProductCreate
    from app.modules.products import service as product_service

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
    from app.modules.products.schemas import ProductCreate
    from app.modules.products import service as product_service

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
```

### Audit Module Fixtures (`tests/modules/audit/conftest.py`)

```python
@pytest_asyncio.fixture
async def test_audit_log(session, test_user):
    """Create a test audit log."""
    from app.modules.audit.schemas import AuditLogCreate
    from app.modules.audit import service as audit_service

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
```

## Testing Conventions

### Naming Convention

- **Test classes**: `TestOrderService`, `TestOrderAPI`, etc.
- **Test methods**: `test_<action>_<condition>` pattern
    - Examples: `test_create_order_success`, `test_update_status_invalid_transition`
- **Unique identifiers**: Use UUID suffixes to avoid conflicts

  ```python
  unique_id = str(uuid.uuid4())[:8]
  sku = f"TEST-{unique_id}"
  ```

### Assertions

**Service Tests:**

```python
# Assert return value
assert order.id is not None
assert order.status == OrderStatus.PENDING.value

# Assert exception
with pytest.raises(NotFoundException) as exc_info:
    await order_service.get_order_by_id(session, 99999)
assert "not found" in str(exc_info.value)
```

**API Tests:**

```python
# Assert status code
assert response.status_code == status.HTTP_201_CREATED

# Assert response structure
data = response.json()
assert data["success"] is True
assert "data" in data
assert "message" in data

# Assert error response
assert response.status_code == status.HTTP_404_NOT_FOUND
assert "detail" in response.json()
```

### Error Case Handling

| Exception               | HTTP Status | Test Focus                                                   |
| ----------------------- | ----------- | ------------------------------------------------------------ |
| `NotFoundException`     | 404         | Error message contains resource identifier                   |
| `ConflictException`     | 409         | Duplicate resource (SKU, email, etc.)                        |
| `ValidationException`   | 422         | Business rule violation (invalid status transition)          |
| `UnauthorizedException` | 401         | Missing or invalid token                                     |
| Forbidden               | 403         | Insufficient privileges (non-admin accessing admin endpoint) |

### Test Isolation

- Each test uses the `session` fixture with auto-rollback
- No shared state between tests
- Tests can run in any order (no dependencies)
- UUID-based identifiers prevent conflicts

### Pytest Markers

```python
@pytest.mark.asyncio
class TestOrderService:
    # All tests in class are async
    async def test_create_order_success(self, session):
        ...
```

## Coverage Goals

### Target Metrics

| Module    | Service Tests | API Tests | Total   |
| --------- | ------------- | --------- | ------- |
| Orders    | 25            | 20        | 45      |
| Products  | 20            | 18        | 38      |
| Audit     | 15            | 12        | 27      |
| **Total** | **60**        | **50**    | **110** |

### Coverage Targets

- **Service layer**: 90%+ line coverage for:
    - `app/modules/orders/service.py`
    - `app/modules/products/service.py`
    - `app/modules/audit/service.py`

- **API endpoints**: 100% endpoint coverage
    - All routes tested
    - All HTTP methods tested
    - All query parameters tested

- **Business rules**: 100% coverage
    - All validation logic
    - All status transitions
    - All uniqueness checks

### Running Tests

```bash
# Run all tests
just test

# Run specific module tests
uv run pytest tests/modules/orders -v
uv run pytest tests/modules/products -v
uv run pytest tests/modules/audit -v

# Run with coverage
uv run pytest tests/modules/orders tests/modules/products tests/modules/audit \
    -v --cov=app/modules/orders --cov=app/modules/products --cov=app/modules/audit \
    --cov-report=term-missing
```

## Implementation Notes

### Mocking Celery Tasks

For order creation tests, the Celery task dispatch should be mocked to avoid actual task execution:

```python
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_create_order_dispatches_timeout_task(session, test_user, test_product_for_order):
    with patch("app.modules.orders.service.dispatch") as mock_dispatch:
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[OrderItemCreate(...)]
        )
        await order_service.create_order(session, order_in)

        # Verify dispatch was called
        mock_dispatch.assert_called_once()
```

### Testing Pagination

Pagination tests should verify:

- Correct number of items returned
- Total count is accurate
- Total pages calculation

```python
async def test_get_products_pagination(client, superuser_headers, multiple_products):
    response = await client.get(
        "/api/v1/products?page=1&page_size=3",
        headers=superuser_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 3
    assert data["total"] == 5
    assert data["total_pages"] == 2
```

### Testing Status Transitions

Each invalid transition should be tested individually to provide clear error messages:

```python
@pytest.mark.parametrize("current_status,new_status", [
    ("COMPLETED", "PENDING"),
    ("COMPLETED", "CANCELLED"),
    ("CANCELLED", "PENDING"),
    ("PENDING", "SHIPPED"),  # Skip transition
])
async def test_update_status_invalid_transition(
    self, session, test_order, current_status, new_status
):
    test_order.status = current_status
    await session.commit()

    with pytest.raises(ValidationException) as exc_info:
        await order_service.update_order_status(
            session, test_order.id, OrderUpdate(status=OrderStatus(new_status))
        )
    assert "Cannot transition" in str(exc_info.value)
```

## Success Criteria

1. **All test cases pass**: 110+ tests run successfully
2. **Coverage targets met**: 90%+ service layer coverage, 100% endpoint coverage
3. **No regression**: Existing tests continue to pass
4. **CI/CD integration**: Tests run in GitHub Actions workflow
5. **Documentation**: Test names clearly describe what's being tested

## Future Enhancements

1. **Config module tests**: Add comprehensive tests for system configuration CRUD
2. **Notifications module tests**: Add tests when implementation is complete
3. **Integration tests**: Add tests for cross-module interactions (e.g., order creation updates inventory)
4. **Performance tests**: Add tests for bulk operations and large datasets
5. **Edge case expansion**: Add more boundary value tests for all numeric fields
