# Background Tasks System Design

## Summary

Implement a background task system using Celery + Redis for the Enterprise FastAPI project. The system supports asynchronous task execution, automatic retry with dead letter queue, scheduled tasks, and task monitoring API.

## Goals

- Support 4 initial task types: order timeout cancellation, notification sending, data export, audit log async write
- Automatic retry with configurable max retries and dead letter status
- Task status tracking in database for business queries and audit
- API for task monitoring and management
- Periodic scheduled tasks via celery-beat
- Tasks belong to business modules, not centralized

## Technology Choice: Celery + Redis

**Why Celery over ARQ:**

- Mature community, extensive documentation
- Built-in retry, task routing, rate limiting
- celery-beat for periodic tasks (industry standard)
- Flower monitoring UI available
- Better enterprise reliability

**Trade-off:** More complex configuration than ARQ, but one-time cost.

---

## Section 1: Data Model

### TaskRecord Table (User Database)

Model uses SQLAlchemy 2.0 `Mapped`/`mapped_column` syntax, consistent with existing codebase. Inherits `UserBase` (which applies `TimestampMixin`), so `created_at` and `updated_at` are inherited automatically.

```python
from enum import StrEnum
from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import UserBase


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DEAD = "DEAD"
    CANCELLED = "CANCELLED"


class TaskRecord(UserBase):
    __tablename__ = "task_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.PENDING.value, nullable=False, index=True)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

### Field Reference

| Field          | Type     | Description                                             |
| -------------- | -------- | ------------------------------------------------------- |
| id             | int      | Primary key                                             |
| task_name      | str      | Business identifier (e.g. `orders.cancel_timeout`)      |
| celery_task_id | str      | Celery task ID for correlation                          |
| status         | enum     | PENDING / RUNNING / SUCCESS / FAILED / DEAD / CANCELLED |
| params         | JSON     | Task parameters (per-task schema, see Section 7)        |
| error          | text     | Error message (empty on success)                        |
| retry_count    | int      | Number of retries attempted                             |
| scheduled_at   | datetime | Planned execution time                                  |
| created_at     | datetime | Inherited from TimestampMixin                           |
| updated_at     | datetime | Inherited from TimestampMixin                           |
| completed_at   | datetime | Completion time                                         |

### Status Flow

```text
PENDING → RUNNING → SUCCESS/FAILED → (retry) → DEAD
PENDING → CANCELLED (manual cancel)
```

### CronTask Removed

Static periodic tasks are configured in `celery-beat` configuration file. No separate table needed.

---

## Section 2: Module Structure

### Infrastructure: `app/tasks/`

Located at `app/tasks/` (not `app/modules/tasks/`) because it provides cross-cutting infrastructure consumed by all modules. This is similar to how `app/db/` and `app/common/` are structured outside `app/modules/`.

```text
app/tasks/
├── __init__.py
├── celery_app.py       # Celery instance configuration
├── beat_schedule.py    # Periodic task definitions
├── dispatcher.py       # Transaction-safe task dispatch
├── signals.py          # Auto status sync via Celery signals
├── db.py               # Sync session factory for Celery workers
├── models.py           # TaskRecord model
├── schemas.py          # Pydantic schemas
├── repository.py       # Database access layer
├── service.py          # Business logic (create, query, status update)
└── router.py           # Task monitoring API
```

### Business Modules: `app/modules/*/tasks.py`

Each business module owns its tasks:

```text
app/modules/orders/tasks.py       # cancel_timeout
app/modules/notifications/         # New module: notification tasks + basic service
├── __init__.py
├── tasks.py                      # send_notification
├── service.py                    # Notification delivery logic
└── schemas.py                    # Notification schemas
app/modules/exports/tasks.py      # export_order_data
app/modules/audit/tasks.py        # write_audit_log
```

**Design Principle:** Tasks only call service layer, never repository directly.

### Async/Sync Bridge: `app/tasks/db.py`

Celery workers are synchronous. The project uses async SQLAlchemy everywhere. A dedicated sync session factory bridges this gap:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings

sync_engine = create_engine(
    settings.USER_DATABASE_URL.replace("+asyncpg", "").replace("+aiomysql", ""),
    pool_pre_ping=True,
)

SyncSessionLocal = Session(autocommit=False, autoflush=False, bind=sync_engine)


def get_sync_session():
    """Yield a sync session for Celery worker tasks."""
    session = SyncSessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

This is used by:

- Signal handlers (Section 4)
- Task functions (Section 7)
- Repository layer for tasks

---

## Section 3: Dispatcher (Transaction Safety)

The dispatcher ensures TaskRecord and Celery task stay in sync:

```python
from app.tasks.db import get_sync_session
from app.tasks.repository import create_task_record, update_celery_task_id, update_task_status


def dispatch(task, *args, **kwargs):
    """Create TaskRecord + dispatch Celery task atomically.

    Uses sync session because Celery's apply_async() is a synchronous Redis call.
    The TaskRecord is created first, then Celery task is dispatched.
    If dispatch fails, TaskRecord is marked FAILED.
    """
    session = next(get_sync_session())
    try:
        record = create_task_record(session, task.name, args, kwargs)
        result = task.apply_async(args=args, kwargs=kwargs)
        update_celery_task_id(session, record.id, result.id)
        session.commit()
        return record
    except Exception as e:
        session.rollback()
        record = create_task_record(session, task.name, args, kwargs)
        update_task_status(session, record.id, "FAILED", error=f"Dispatch failed: {e}")
        session.commit()
        raise
    finally:
        session.close()
```

Business code calls:

```python
from app.tasks.dispatcher import dispatch
from app.modules.orders.tasks import cancel_timeout

dispatch(cancel_timeout, order.id, countdown=1800)
```

### Deduplication

To prevent duplicate dispatch (e.g., two `cancel_timeout` for the same order), tasks should check for existing pending records:

```python
def dispatch(task, *args, **kwargs):
    session = next(get_sync_session())
    try:
        # Check for existing pending task with same name + params
        existing = find_pending_task(session, task.name, args, kwargs)
        if existing:
            return existing  # Idempotent: return existing record

        record = create_task_record(session, task.name, args, kwargs)
        # ... rest of dispatch logic
    finally:
        session.close()
```

---

## Section 4: Status Sync via Celery Signals

Celery signals automatically update TaskRecord. Signal handlers are synchronous and use the sync session factory:

```python
from celery.signals import task_prerun, task_postrun, task_failure

from app.tasks.db import get_sync_session
from app.tasks.repository import update_task_status_by_celery_id


@task_prerun.connect
def task_started(sender, task_id, **kwargs):
    session = next(get_sync_session())
    try:
        update_task_status_by_celery_id(session, task_id, "RUNNING")
        session.commit()
    finally:
        session.close()


@task_postrun.connect
def task_completed(sender, task_id, retval, state, **kwargs):
    session = next(get_sync_session())
    try:
        status = "SUCCESS" if state == "SUCCESS" else "FAILED"
        update_task_status_by_celery_id(session, task_id, status, result=retval)
        session.commit()
    finally:
        session.close()


@task_failure.connect
def task_failed(sender, task_id, exception, **kwargs):
    session = next(get_sync_session())
    try:
        update_task_status_by_celery_id(session, task_id, "FAILED", error=str(exception))
        session.commit()
    finally:
        session.close()
```

---

## Section 5: API Endpoints

### Task Monitoring (Requires Superuser Auth)

All task endpoints require authentication, following existing pattern `Depends(get_current_active_superuser)`.

```text
GET    /api/v1/tasks                    # Task list (pagination, filters)
GET    /api/v1/tasks/{task_id}          # Task detail
POST   /api/v1/tasks/{task_id}/retry    # Manual retry failed task
POST   /api/v1/tasks/{task_id}/revive   # Reset DEAD to PENDING
DELETE /api/v1/tasks/{task_id}          # Cancel pending task
```

### Query Parameters

| Param     | Type | Description         |
| --------- | ---- | ------------------- |
| status    | str  | Filter by status    |
| task_name | str  | Filter by task name |
| page      | int  | Page number         |
| page_size | int  | Items per page      |

### Response Schemas

Follow existing project patterns (`DataResponse`, `PaginatedResponse` from `app/common/schemas.py`).

```python
class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_name: str
    celery_task_id: str | None
    status: TaskStatus
    params: dict | None
    error: str | None
    retry_count: int
    scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
```

---

## Section 6: Celery Configuration

### celery_app.py

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "enterprise_fastapi",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_max_retries=3,
    task_default_retry_delay=60,
    task_time_limit=300,            # Hard limit: 5 minutes
    task_soft_time_limit=240,       # Soft limit: 4 minutes
)

# Import tasks to register them
celery_app.autodiscover_tasks(["app.modules.orders", "app.modules.notifications", "app.modules.exports", "app.modules.audit"])
```

### settings.py

```python
CELERY_BROKER_URL: str = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
ORDER_CANCEL_TIMEOUT: int = 1800   # 30 minutes (configurable for testing)
```

### justfile Commands

```just
worker:
    uv run celery -A app.tasks.celery_app worker --loglevel=info

beat:
    uv run celery -A app.tasks.celery_app beat --loglevel=info
```

---

## Section 7: Task Definitions

### Per-Task Parameter Schemas

Each task type has a defined parameter schema for type safety:

```python
# app/modules/orders/schemas.py (add to existing)
class CancelTimeoutParams(BaseModel):
    order_id: int

# app/modules/notifications/schemas.py
class SendNotificationParams(BaseModel):
    user_id: int
    template: str
    context: dict

# app/modules/exports/schemas.py
class ExportOrderParams(BaseModel):
    filters: dict
    format: str = "csv"
```

### Order Timeout Cancellation

```python
# app/modules/orders/tasks.py
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_session


@celery_app.task(bind=True, max_retries=3, retry_backoff=True)
def cancel_timeout(self, order_id: int):
    session = next(get_sync_session())
    try:
        from app.modules.orders.service import get_order_by_id, cancel_order

        order = get_order_by_id(session, order_id)

        # Idempotent: only cancel if still PENDING
        if order.status != "PENDING":
            return {"skipped": True, "reason": f"status is {order.status}"}

        cancel_order(session, order_id)
        session.commit()
        return {"cancelled": True}
    except Exception as exc:
        session.rollback()
        raise self.retry(exc=exc)
    finally:
        session.close()
```

### Notification Sending

```python
# app/modules/notifications/tasks.py
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_session


@celery_app.task(bind=True, max_retries=3, retry_backoff=True)
def send_notification(self, user_id: int, template: str, context: dict):
    session = next(get_sync_session())
    try:
        from app.modules.notifications.service import deliver_notification

        # Idempotent: check if already sent
        deliver_notification(session, user_id, template, context)
        session.commit()
        return {"sent": True}
    except Exception as exc:
        session.rollback()
        raise self.retry(exc=exc)
    finally:
        session.close()
```

### Data Export

```python
# app/modules/exports/tasks.py
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_session


@celery_app.task(bind=True, max_retries=2, retry_backoff=True)
def export_order_data(self, filters: dict, format: str = "csv"):
    session = next(get_sync_session())
    try:
        from app.modules.orders.service import get_orders_for_export

        orders = get_orders_for_export(session, filters)
        file_path = generate_csv(orders) if format == "csv" else generate_excel(orders)
        session.commit()
        return {"file_path": file_path}
    except Exception as exc:
        session.rollback()
        raise self.retry(exc=exc)
    finally:
        session.close()
```

### Audit Log

```python
# app/modules/audit/tasks.py
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_session


@celery_app.task
def write_audit_log(user_id: int, action: str, resource_type: str, resource_id: int, **kwargs):
    session = next(get_sync_session())
    try:
        from app.modules.audit.service import create_audit_log

        create_audit_log(session, user_id, action, resource_type, resource_id, **kwargs)
        session.commit()
        return {"logged": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

---

## Section 8: Error Handling

### Retry Strategy

- Max retries: 3 (configurable per task)
- Retry delay: Exponential backoff (`retry_backoff=True` in task decorator)
- Final failure: Status set to DEAD

### Dead Letter Handling

- DEAD tasks stored in TaskRecord for investigation
- POST `/api/v1/tasks/{id}/revive` resets to PENDING and re-dispatches
- Manual inspection via task query API

### Task Cancellation

- When order is paid, cancel pending timeout task with `terminate=True`:

```python
task_record = await get_pending_task("orders.cancel_timeout", order_id)
if task_record:
    celery_app.control.revoke(task_record.celery_task_id, terminate=True)
    await update_task_status(task_record.id, "CANCELLED")
```

---

## Section 9: Testing Strategy

### Test Layers

| Layer       | Tool                    | Scope                         |
| ----------- | ----------------------- | ----------------------------- |
| Unit        | pytest + mock           | Task logic, dispatcher        |
| Integration | pytest + testcontainers | Celery + Redis real execution |
| API         | httpx + TestClient      | Task endpoints                |

### Test Structure

```text
tests/modules/tasks/
├── conftest.py              # Shared fixtures
├── test_task_api.py         # API tests
├── test_task_service.py     # Business logic tests
├── test_dispatcher.py       # Dispatcher tests
├── test_signals.py          # Signal handler tests
├── test_integration.py      # Full integration tests
└── jobs/
    ├── test_orders.py
    ├── test_notifications.py
    ├── test_exports.py
    └── test_audit.py
```

### Key Fixtures

```python
@pytest.fixture
def mock_celery(monkeypatch):
    """Unit test: mock Celery calls"""
    ...

@pytest.fixture
async def redis_container():
    """Integration test: testcontainers Redis"""
    ...

@pytest.fixture
def eager_celery():
    """Quick task logic validation"""
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False
```

---

## Section 10: Implementation Order

| Step | Content                                               | Risk   |
| ---- | ----------------------------------------------------- | ------ |
| 1    | Install Celery + Redis dependencies                   | Low    |
| 2    | Create TaskRecord model + sync DB session + migration | Low    |
| 3    | Implement dispatcher + signals                        | Medium |
| 4    | Implement service + repository                        | Low    |
| 5    | Implement task query API                              | Low    |
| 6    | Implement orders/tasks.py                             | Medium |
| 7    | Implement notifications module + tasks.py             | Low    |
| 8    | Implement exports/tasks.py                            | Low    |
| 9    | Implement audit/tasks.py                              | Low    |
| 10   | Integration tests + Flower                            | Medium |

### Verification

Each step: `just lint && just test`

Final:

```bash
just db-migrate "add tasks module"
just db-upgrade
just run
celery -A app.tasks.celery_app worker --loglevel=info
```

---

## Verification Criteria

- All existing tests pass after each step
- New task tests pass
- `just lint` clean
- `just test` all green
- Worker processes tasks correctly
- Task status syncs to database
- Retry and dead letter work as expected
- API endpoints return correct task information
