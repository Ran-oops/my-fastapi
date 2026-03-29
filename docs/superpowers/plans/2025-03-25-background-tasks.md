# Background Tasks System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a Celery + Redis background task system with automatic retry, dead letter queue, task monitoring API, and 4 initial task types (order timeout, notifications, export, audit).

**Architecture:** Tasks belong to business modules (`app/modules/*/tasks.py`). Cross-cutting infrastructure lives in `app/tasks/`. Celery workers use a sync database session bridge since the project is async-first. Signal handlers auto-sync task status to database.

**Tech Stack:** Celery, Redis, SQLAlchemy 2.0 (sync for workers), Pydantic V2

---

## File Structure

### New Files

| File                                             | Responsibility                         |
| ------------------------------------------------ | -------------------------------------- |
| `app/tasks/__init__.py`                          | Package init, re-exports               |
| `app/tasks/celery_app.py`                        | Celery instance + configuration        |
| `app/tasks/beat_schedule.py`                     | Periodic task definitions              |
| `app/tasks/db.py`                                | Sync session factory for workers       |
| `app/tasks/dispatcher.py`                        | Transaction-safe task dispatch         |
| `app/tasks/signals.py`                           | Celery signal handlers for status sync |
| `app/tasks/models.py`                            | TaskRecord model                       |
| `app/tasks/schemas.py`                           | Pydantic schemas for tasks             |
| `app/tasks/repository.py`                        | Database access layer (sync)           |
| `app/tasks/service.py`                           | Business logic for task management     |
| `app/tasks/router.py`                            | Task monitoring API endpoints          |
| `app/modules/notifications/__init__.py`          | Package init                           |
| `app/modules/notifications/tasks.py`             | send_notification task                 |
| `app/modules/notifications/service.py`           | Notification delivery logic            |
| `app/modules/notifications/schemas.py`           | Notification schemas                   |
| `app/modules/orders/tasks.py`                    | cancel_timeout task                    |
| `app/modules/exports/__init__.py`                | Package init                           |
| `app/modules/exports/tasks.py`                   | export_order_data task                 |
| `app/modules/audit/tasks.py`                     | write_audit_log task                   |
| `tests/modules/tasks/conftest.py`                | Shared test fixtures                   |
| `tests/modules/tasks/test_task_api.py`           | API endpoint tests                     |
| `tests/modules/tasks/test_task_service.py`       | Service layer tests                    |
| `tests/modules/tasks/test_dispatcher.py`         | Dispatcher tests                       |
| `tests/modules/tasks/test_signals.py`            | Signal handler tests                   |
| `tests/modules/tasks/jobs/test_orders.py`        | Order task tests                       |
| `tests/modules/tasks/jobs/test_notifications.py` | Notification task tests                |
| `tests/modules/tasks/jobs/test_exports.py`       | Export task tests                      |
| `tests/modules/tasks/jobs/test_audit.py`         | Audit task tests                       |

### Modified Files

| File                            | Change                                       |
| ------------------------------- | -------------------------------------------- |
| `pyproject.toml`                | Add celery + redis dependencies              |
| `app/core/config.py`            | Add CELERY_BROKER_URL, CELERY_RESULT_BACKEND |
| `app/api/v1/__init__.py`        | Register tasks router                        |
| `app/modules/orders/service.py` | Call cancel_timeout on order creation        |
| `justfile`                      | Add worker, beat commands                    |

### Key Design Decision: Sync Queries for Celery Workers

The existing repositories (`order_repo`, `audit_log_repo`) are all async and expect `AsyncSession`. Celery workers are synchronous. Therefore, **task functions use raw sync SQLAlchemy queries** instead of calling existing async repositories. This keeps the async/sync boundary clean.

---

## Task 1: Install Dependencies + Configure Celery

**Files:**

- Modify: `pyproject.toml`
- Create: `app/tasks/__init__.py`
- Create: `app/tasks/celery_app.py`
- Create: `app/tasks/beat_schedule.py`
- Modify: `app/core/config.py`

- [ ] **Step 1: Add Celery dependencies to pyproject.toml**

```toml
# Add to [project] dependencies:
"celery[redis]>=5.3.0",
"redis>=5.0.0",
```

- [ ] **Step 2: Install dependencies**

Run: `uv sync`
Expected: Dependencies installed successfully

- [ ] **Step 3: Add Celery config to settings**

```python
# app/core/config.py - add to Settings class:
CELERY_BROKER_URL: str = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
ORDER_CANCEL_TIMEOUT: int = 1800
```

- [ ] **Step 4: Create app/tasks/**init**.py**

```python
```

- [ ] **Step 5: Create app/tasks/celery_app.py**

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
    task_time_limit=300,
    task_soft_time_limit=240,
)

# Import signals to register them
import app.tasks.signals  # noqa: F401, E402
```

- [ ] **Step 6: Create app/tasks/beat_schedule.py**

```python
from celery.schedules import crontab

beat_schedule = {
    # Add periodic tasks here as needed
    # "cleanup-expired-data": {
    #     "task": "audit.cleanup_expired",
    #     "schedule": crontab(hour=2, minute=0),
    # },
}
```

- [ ] **Step 7: Verify import works**

Run: `python -c "from app.tasks.celery_app import celery_app; print('OK')"`
Expected: OK

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml app/core/config.py app/tasks/__init__.py app/tasks/celery_app.py app/tasks/beat_schedule.py
git commit -m "feat(tasks): add Celery dependencies and configuration"
```

---

## Task 2: Create Sync DB Bridge + TaskRecord Model

**Files:**

- Create: `app/tasks/db.py`
- Create: `app/tasks/models.py`

- [ ] **Step 1: Create app/tasks/db.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Convert async URL to sync URL
sync_url = (
    settings.USER_DATABASE_URL
    .replace("+asyncpg", "")
    .replace("+aiomysql", "")
    .replace("+aioodbc", "")
)

sync_engine = create_engine(sync_url, pool_pre_ping=True)

SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


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

- [ ] **Step 2: Create app/tasks/models.py**

```python
from __future__ import annotations

from datetime import datetime
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

- [ ] **Step 3: Verify import works**

Run: `python -c "from app.tasks.models import TaskRecord, TaskStatus; print('OK')"`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add app/tasks/db.py app/tasks/models.py
git commit -m "feat(tasks): add sync DB bridge and TaskRecord model"
```

---

## Task 3: Create Repository + Service Layer

**Files:**

- Create: `app/tasks/repository.py`
- Create: `app/tasks/service.py`
- Create: `app/tasks/schemas.py`

- [ ] **Step 1: Create app/tasks/schemas.py**

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.tasks.models import TaskStatus


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

- [ ] **Step 2: Create app/tasks/repository.py**

```python
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.tasks.models import TaskRecord, TaskStatus


def create_task_record(session: Session, task_name: str, params: dict | None = None) -> TaskRecord:
    record = TaskRecord(task_name=task_name, params=params, status=TaskStatus.PENDING.value)
    session.add(record)
    session.flush()
    return record


def update_celery_task_id(session: Session, record_id: int, celery_task_id: str) -> None:
    record = session.get(TaskRecord, record_id)
    if record:
        record.celery_task_id = celery_task_id
        session.flush()


def update_task_status(session: Session, record_id: int, status: str, error: str | None = None) -> None:
    record = session.get(TaskRecord, record_id)
    if record:
        record.status = status
        if error:
            record.error = error
        if status in (TaskStatus.SUCCESS.value, TaskStatus.FAILED.value, TaskStatus.DEAD.value):
            record.completed_at = datetime.now(timezone.utc)
        session.flush()


def update_task_status_by_celery_id(session: Session, celery_task_id: str, status: str, error: str | None = None) -> None:
    record = session.query(TaskRecord).filter(TaskRecord.celery_task_id == celery_task_id).first()
    if record:
        record.status = status
        if error:
            record.error = error
        if status in (TaskStatus.SUCCESS.value, TaskStatus.FAILED.value, TaskStatus.DEAD.value):
            record.completed_at = datetime.now(timezone.utc)
        session.flush()


def find_pending_task(session: Session, task_name: str, params: dict | None = None) -> TaskRecord | None:
    query = session.query(TaskRecord).filter(
        TaskRecord.task_name == task_name,
        TaskRecord.status == TaskStatus.PENDING.value,
    )
    if params:
        query = query.filter(TaskRecord.params == params)
    return query.first()


def get_task_by_id(session: Session, task_id: int) -> TaskRecord | None:
    return session.get(TaskRecord, task_id)


def get_tasks(session: Session, status: str | None = None, task_name: str | None = None, skip: int = 0, limit: int = 10) -> tuple[list[TaskRecord], int]:
    query = session.query(TaskRecord)
    if status:
        query = query.filter(TaskRecord.status == status)
    if task_name:
        query = query.filter(TaskRecord.task_name == task_name)
    total = query.count()
    records = query.order_by(TaskRecord.created_at.desc()).offset(skip).limit(limit).all()
    return list(records), total
```

- [ ] **Step 3: Create app/tasks/service.py**

```python
from sqlalchemy.orm import Session

from app.tasks.repository import get_task_by_id, get_tasks, update_task_status
from app.tasks.models import TaskStatus


def get_task(session: Session, task_id: int):
    return get_task_by_id(session, task_id)


def list_tasks(session: Session, status: str | None = None, task_name: str | None = None, page: int = 1, page_size: int = 10):
    skip = (page - 1) * page_size
    return get_tasks(session, status=status, task_name=task_name, skip=skip, limit=page_size)


def retry_task(session: Session, task_id: int):
    from app.tasks.dispatcher import dispatch_by_task_name

    task_record = get_task_by_id(session, task_id)
    if not task_record:
        raise ValueError("Task not found")
    if task_record.status not in (TaskStatus.FAILED.value, TaskStatus.DEAD.value):
        raise ValueError(f"Cannot retry task with status {task_record.status}")

    update_task_status(session, task_id, TaskStatus.PENDING.value)
    session.commit()
    dispatch_by_task_name(task_record.task_name, task_record.params or {})
    return task_record


def cancel_task(session: Session, task_id: int):
    from app.tasks.celery_app import celery_app

    task_record = get_task_by_id(session, task_id)
    if not task_record:
        raise ValueError("Task not found")
    if task_record.status != TaskStatus.PENDING.value:
        raise ValueError(f"Cannot cancel task with status {task_record.status}")

    if task_record.celery_task_id:
        celery_app.control.revoke(task_record.celery_task_id, terminate=True)

    update_task_status(session, task_id, TaskStatus.CANCELLED.value)
    session.commit()
    return task_record
```

- [ ] **Step 4: Verify imports**

Run: `python -c "from app.tasks.repository import create_task_record; from app.tasks.service import get_task; print('OK')"`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add app/tasks/repository.py app/tasks/service.py app/tasks/schemas.py
git commit -m "feat(tasks): add repository, service, and schemas"
```

---

## Task 4: Create Dispatcher

**Files:**

- Create: `app/tasks/dispatcher.py`

- [ ] **Step 1: Create app/tasks/dispatcher.py**

```python
from app.tasks.db import get_sync_session
from app.tasks.repository import create_task_record, update_celery_task_id, update_task_status, find_pending_task


def dispatch(task, *args, **kwargs):
    """Create TaskRecord + dispatch Celery task atomically."""
    session = next(get_sync_session())
    try:
        # Extract Celery-specific kwargs
        countdown = kwargs.pop("countdown", None)
        eta = kwargs.pop("eta", None)

        params = {"args": list(args), "kwargs": kwargs}

        # Deduplication: check for existing pending task
        existing = find_pending_task(session, task.name, params)
        if existing:
            return existing

        record = create_task_record(session, task.name, params=params)

        # Dispatch to Celery
        apply_kwargs = {}
        if countdown is not None:
            apply_kwargs["countdown"] = countdown
        if eta is not None:
            apply_kwargs["eta"] = eta

        result = task.apply_async(args=args, kwargs=kwargs, **apply_kwargs)
        update_celery_task_id(session, record.id, result.id)
        session.commit()
        return record
    except Exception as e:
        session.rollback()
        # Update original record as FAILED instead of creating a new one
        try:
            update_task_status(session, record.id, "FAILED", error=f"Dispatch failed: {e}")
            session.commit()
        except Exception:
            session.rollback()
        raise
    finally:
        session.close()


def dispatch_by_task_name(task_name: str, params: dict):
    """Dispatch a task by its registered name (for retry/revive)."""
    from app.tasks.celery_app import celery_app

    task = celery_app.tasks.get(task_name)
    if not task:
        raise ValueError(f"Task {task_name} not registered")

    args = params.get("args", [])
    kwargs = params.get("kwargs", {})
    dispatch(task, *args, **kwargs)
```

- [ ] **Step 2: Verify import**

Run: `python -c "from app.tasks.dispatcher import dispatch; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add app/tasks/dispatcher.py
git commit -m "feat(tasks): add transaction-safe dispatcher"
```

---

## Task 5: Create Signal Handlers

**Files:**

- Create: `app/tasks/signals.py`

- [ ] **Step 1: Create app/tasks/signals.py**

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
    except Exception:
        session.rollback()
    finally:
        session.close()


@task_postrun.connect
def task_completed(sender, task_id, retval, state, **kwargs):
    session = next(get_sync_session())
    try:
        status = "SUCCESS" if state == "SUCCESS" else "FAILED"
        update_task_status_by_celery_id(session, task_id, status)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@task_failure.connect
def task_failed(sender, task_id, exception, **kwargs):
    session = next(get_sync_session())
    try:
        update_task_status_by_celery_id(session, task_id, "FAILED", error=str(exception))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
```

- [ ] **Step 2: Verify import**

Run: `python -c "from app.tasks.signals import task_started; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add app/tasks/signals.py
git commit -m "feat(tasks): add Celery signal handlers for status sync"
```

---

## Task 6: Create Task Query API

**Files:**

- Create: `app/tasks/router.py`
- Modify: `app/api/v1/__init__.py`

- [ ] **Step 1: Create app/tasks/router.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import get_current_active_superuser
from app.common.pagination import PaginatedResponse
from app.tasks.schemas import TaskRead
from app.tasks.service import get_task, list_tasks, retry_task, cancel_task
from app.tasks.db import get_sync_session
from app.tasks.models import TaskStatus

router = APIRouter()


@router.get("", response_model=PaginatedResponse[TaskRead])
def get_tasks(
    status: TaskStatus | None = Query(None),
    task_name: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    _current_user=Depends(get_current_active_superuser),
):
    session = next(get_sync_session())
    try:
        status_value = status.value if status else None
        records, total = list_tasks(session, status=status_value, task_name=task_name, page=page, page_size=page_size)
        total_pages = (total + page_size - 1) // page_size
        return PaginatedResponse(
            data=[TaskRead.model_validate(r) for r in records],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    finally:
        session.close()


@router.get("/{task_id}", response_model=TaskRead)
def get_task_detail(
    task_id: int,
    _current_user=Depends(get_current_active_superuser),
):
    session = next(get_sync_session())
    try:
        task_record = get_task(session, task_id)
        if not task_record:
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskRead.model_validate(task_record)
    finally:
        session.close()


@router.post("/{task_id}/retry", response_model=TaskRead)
def retry_failed_task(
    task_id: int,
    _current_user=Depends(get_current_active_superuser),
):
    session = next(get_sync_session())
    try:
        task_record = retry_task(session, task_id)
        return TaskRead.model_validate(task_record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()


@router.post("/{task_id}/revive", response_model=TaskRead)
def revive_dead_task(
    task_id: int,
    _current_user=Depends(get_current_active_superuser),
):
    session = next(get_sync_session())
    try:
        task_record = retry_task(session, task_id)
        return TaskRead.model_validate(task_record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()


@router.delete("/{task_id}", response_model=TaskRead)
def cancel_pending_task(
    task_id: int,
    _current_user=Depends(get_current_active_superuser),
):
    session = next(get_sync_session())
    try:
        task_record = cancel_task(session, task_id)
        return TaskRead.model_validate(task_record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()
```

- [ ] **Step 2: Register router in app/api/v1/**init**.py**

Add imports:

```python
from app.tasks.router import router as tasks_router
```

Add router registration:

```python
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
```

- [ ] **Step 3: Run lint check**

Run: `just lint`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add app/tasks/router.py app/api/v1/__init__.py
git commit -m "feat(tasks): add task monitoring API endpoints"
```

---

## Task 7: Create Order Timeout Task

**Files:**

- Create: `app/modules/orders/tasks.py`
- Modify: `app/modules/orders/service.py`

- [ ] **Step 1: Create app/modules/orders/tasks.py**

```python
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_session
from app.modules.orders.models import Order, OrderStatus


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
```

- [ ] **Step 2: Modify app/modules/orders/service.py**

Add import at top:

```python
from app.tasks.dispatcher import dispatch
from app.modules.orders.tasks import cancel_timeout
from app.core.config import settings
```

Add after `order_repo.create()` in `create_order` function:

```python
dispatch(cancel_timeout, order.id, countdown=settings.ORDER_CANCEL_TIMEOUT)
```

- [ ] **Step 3: Verify import**

Run: `python -c "from app.modules.orders.tasks import cancel_timeout; print('OK')"`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add app/modules/orders/tasks.py app/modules/orders/service.py
git commit -m "feat(tasks): add order timeout cancellation task"
```

---

## Task 8: Create Notification Module + Task

**Files:**

- Create: `app/modules/notifications/__init__.py`
- Create: `app/modules/notifications/schemas.py`
- Create: `app/modules/notifications/service.py`
- Create: `app/modules/notifications/tasks.py`

- [ ] **Step 1: Create app/modules/notifications/**init**.py**

```python
```

- [ ] **Step 2: Create app/modules/notifications/schemas.py**

```python
from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    user_id: int
    template: str
    context: dict = Field(default_factory=dict)
```

- [ ] **Step 3: Create app/modules/notifications/service.py**

```python
def deliver_notification(user_id: int, template: str, context: dict) -> dict:
    """Deliver notification to user. Placeholder implementation."""
    # TODO: Implement actual notification delivery (email, SMS, in-app)
    print(f"[Notification] user_id={user_id}, template={template}, context={context}")
    return {"delivered": True}
```

- [ ] **Step 4: Create app/modules/notifications/tasks.py**

```python
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, retry_backoff=True)
def send_notification(self, user_id: int, template: str, context: dict):
    """Send notification to user asynchronously."""
    try:
        from app.modules.notifications.service import deliver_notification

        result = deliver_notification(user_id, template, context)
        return result
    except Exception as exc:
        raise self.retry(exc=exc)
```

- [ ] **Step 5: Register autodiscover in celery_app.py**

Update `app/tasks/celery_app.py`:

```python
celery_app.autodiscover_tasks(["app.modules.orders", "app.modules.notifications", "app.modules.audit"])
```

- [ ] **Step 6: Verify import**

Run: `python -c "from app.modules.notifications.tasks import send_notification; print('OK')"`
Expected: OK

- [ ] **Step 7: Commit**

```bash
git add app/modules/notifications/
git commit -m "feat(tasks): add notification module and task"
```

---

## Task 9: Create Export + Audit Tasks

**Files:**

- Create: `app/modules/exports/__init__.py`
- Create: `app/modules/exports/tasks.py`
- Create: `app/modules/audit/tasks.py`

- [ ] **Step 1: Create app/modules/exports/**init**.py**

```python
```

- [ ] **Step 2: Create app/modules/exports/tasks.py**

```python
import tempfile
import csv

from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_session
from app.modules.orders.models import Order


@celery_app.task(bind=True, max_retries=2, retry_backoff=True)
def export_order_data(self, filters: dict, format: str = "csv"):
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
```

- [ ] **Step 3: Create app/modules/audit/tasks.py**

```python
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_session
from app.modules.audit.models import AuditLog


@celery_app.task
def write_audit_log(user_id: int, action: str, resource_type: str, resource_id: int, **kwargs):
    """Write audit log entry asynchronously."""
    session = next(get_sync_session())
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=kwargs.get("old_value"),
            new_value=kwargs.get("new_value"),
            ip_address=kwargs.get("ip_address"),
        )
        session.add(audit_log)
        session.commit()
        return {"logged": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 4: Verify imports**

Run: `python -c "from app.modules.exports.tasks import export_order_data; from app.modules.audit.tasks import write_audit_log; print('OK')"`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add app/modules/exports/ app/modules/audit/tasks.py
git commit -m "feat(tasks): add export and audit tasks"
```

---

## Task 10: Write Tests

**Files:**

- Create: `tests/modules/tasks/conftest.py`
- Create: `tests/modules/tasks/test_task_service.py`
- Create: `tests/modules/tasks/test_dispatcher.py`
- Create: `tests/modules/tasks/test_task_api.py`
- Create: `tests/modules/tasks/jobs/test_orders.py`

- [ ] **Step 1: Create tests/modules/tasks/conftest.py**

```python
import pytest
from unittest.mock import MagicMock

from app.tasks.celery_app import celery_app


@pytest.fixture
def mock_celery_apply(monkeypatch):
    """Mock Celery apply_async for unit tests."""
    mock_result = MagicMock()
    mock_result.id = "test-task-id-123"
    mock = MagicMock(return_value=mock_result)
    monkeypatch.setattr("celery.app.task.Task.apply_async", mock)
    return mock


@pytest.fixture
def eager_celery():
    """Enable Celery eager mode for quick task logic validation."""
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False
```

- [ ] **Step 2: Create tests/modules/tasks/test_task_service.py**

```python
from app.tasks.models import TaskStatus
from app.tasks.db import get_sync_session


def test_create_task_record():
    """Test creating a task record."""
    from app.tasks.repository import create_task_record

    session = next(get_sync_session())
    try:
        record = create_task_record(session, "test.task", params={"key": "value"})
        session.commit()
        assert record.id is not None
        assert record.task_name == "test.task"
        assert record.status == TaskStatus.PENDING.value
    finally:
        session.close()


def test_update_task_status():
    """Test updating task status."""
    from app.tasks.repository import create_task_record, update_task_status, get_task_by_id

    session = next(get_sync_session())
    try:
        record = create_task_record(session, "test.task")
        session.commit()

        update_task_status(session, record.id, TaskStatus.SUCCESS.value)
        session.commit()

        updated = get_task_by_id(session, record.id)
        assert updated.status == TaskStatus.SUCCESS.value
        assert updated.completed_at is not None
    finally:
        session.close()


def test_find_pending_task():
    """Test finding pending tasks."""
    from app.tasks.repository import create_task_record, find_pending_task

    session = next(get_sync_session())
    try:
        params = {"order_id": 42}
        record = create_task_record(session, "orders.cancel_timeout", params=params)
        session.commit()

        found = find_pending_task(session, "orders.cancel_timeout", params)
        assert found is not None
        assert found.id == record.id
    finally:
        session.close()
```

- [ ] **Step 3: Create tests/modules/tasks/test_dispatcher.py**

```python
import pytest
from unittest.mock import MagicMock


def test_dispatch_creates_task_record(mock_celery_apply):
    """Test that dispatch creates a TaskRecord."""
    from app.tasks.dispatcher import dispatch

    mock_task = MagicMock()
    mock_task.name = "test.task"

    dispatch(mock_task, arg1="value1")

    mock_task.apply_async.assert_called_once()


def test_dispatch_handles_failure():
    """Test that dispatch handles Celery failure gracefully."""
    from app.tasks.dispatcher import dispatch

    mock_task = MagicMock()
    mock_task.name = "test.task"
    mock_task.apply_async.side_effect = Exception("Redis connection failed")

    with pytest.raises(Exception, match="Redis connection failed"):
        dispatch(mock_task, arg1="value1")
```

- [ ] **Step 4: Create tests/modules/tasks/test_task_api.py**

```python
from fastapi.testclient import TestClient


def test_get_tasks_requires_auth(client: TestClient):
    """Test that task endpoints require authentication."""
    response = client.get("/api/v1/tasks")
    assert response.status_code in (401, 403)
```

- [ ] **Step 5: Create tests/modules/tasks/jobs/test_orders.py**

```python
from unittest.mock import patch, MagicMock


def test_cancel_timeout_skips_non_pending():
    """Test that cancel_timeout skips orders that are not PENDING."""
    from app.modules.orders.tasks import cancel_timeout
    from app.modules.orders.models import OrderStatus

    mock_order = MagicMock()
    mock_order.status = OrderStatus.CONFIRMED.value
    mock_order.id = 1

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_order

    with patch("app.modules.orders.tasks.get_sync_session", return_value=iter([mock_session])):
        result = cancel_timeout(1)
        assert result["skipped"] is True
        assert "CONFIRMED" in result["reason"]


def test_cancel_timeout_cancels_pending_order():
    """Test that cancel_timeout cancels PENDING orders."""
    from app.modules.orders.tasks import cancel_timeout
    from app.modules.orders.models import OrderStatus

    mock_order = MagicMock()
    mock_order.status = OrderStatus.PENDING.value
    mock_order.id = 1

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_order

    with patch("app.modules.orders.tasks.get_sync_session", return_value=iter([mock_session])):
        result = cancel_timeout(1)
        assert result["cancelled"] is True
        assert result["order_id"] == 1
        mock_session.commit.assert_called_once()
```

- [ ] **Step 6: Run tests**

Run: `just test`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add tests/modules/tasks/
git commit -m "test(tasks): add unit tests for task system"
```

---

## Task 11: Add Justfile Commands + Generate Migration

**Files:**

- Modify: `justfile`
- Run: Alembic migration

- [ ] **Step 1: Add worker and beat commands to justfile**

Add to `justfile`:

```just
# Start Celery worker
worker:
    uv run celery -A app.tasks.celery_app worker --loglevel=info

# Start Celery beat scheduler
beat:
    uv run celery -A app.tasks.celery_app beat --loglevel=info
```

- [ ] **Step 2: Generate Alembic migration**

Run: `just db-migrate "add tasks module"`
Expected: Migration file created in `alembic/versions/`

- [ ] **Step 3: Review generated migration**

Verify the migration creates `task_records` table with correct columns.

- [ ] **Step 4: Run full lint + test**

Run: `just lint && just test`
Expected: All clean

- [ ] **Step 5: Commit**

```bash
git add justfile alembic/versions/
git commit -m "feat(tasks): add worker commands and database migration"
```

---

## Final Verification

- [ ] All tests pass: `just test`
- [ ] Lint clean: `just lint`
- [ ] Import check: `python -c "from app.main import app; print('OK')"`
- [ ] Start app: `just run`
- [ ] Start worker: `just worker`
- [ ] Check API docs: http://localhost:8000/api/v1/docs
