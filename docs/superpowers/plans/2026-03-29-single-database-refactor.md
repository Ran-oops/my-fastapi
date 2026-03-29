# Single Database Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [`) syntax for tracking.

**Goal:** Refactor from 3-database architecture (PostgreSQL + SQL Server + MySQL) to single database with SQLite fallback.

**Architecture:** Single `DATABASE_URL` config, single engine/session/Base, SQLite default for zero-config development, PostgreSQL for production. All 10 modules use unified `get_session` and `Base`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, aiosqlite, asyncpg

**Spec:** `docs/superpowers/specs/2026-03-29-single-database-refactor-design.md`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `app/core/config.py` | Modify | 3 URLs → 1 `DATABASE_URL`, SQLite default |
| `app/db/base.py` | Modify | 3 Base → 1 `Base` |
| `app/db/session.py` | Modify | 3 engines → 1 engine, 1 `get_session` |
| `app/db/__init__.py` | Modify | Update exports |
| `app/modules/config/models.py` | Modify | `BusinessBase` → `Base` |
| `app/modules/config/router.py` | Modify | `get_business_session` → `get_session` (BUG FIX) |
| `app/modules/users/user_router.py` | Modify | `get_user_session` → `get_session` |
| `app/modules/users/auth_router.py` | Modify | `get_user_session` → `get_session` |
| `app/modules/roles/router.py` | Modify | `get_user_session` → `get_session` |
| `app/modules/orders/router.py` | Modify | `get_user_session` → `get_session` |
| `app/modules/products/router.py` | Modify | `get_user_session` → `get_session` |
| `app/modules/audit/router.py` | Modify | `get_user_session` → `get_session` |
| `app/modules/search/router.py` | Modify | `get_user_session` → `get_session` |
| `app/modules/notifications/router.py` | Modify | `get_user_session` → `get_session` |
| `app/modules/exports/router.py` | Modify | `get_user_session` → `get_session` |
| `app/api/deps.py` | Modify | `get_user_session` → `get_session` |
| `app/main.py` | Modify | Single engine dispose + health check |
| `alembic/env.py` | Modify | Single database URL, unified metadata |
| `alembic/business_db/env.py` | Delete | No longer needed |
| `pyproject.toml` | Modify | Remove aiomysql, aioodbc |
| `.env.example` | Modify | Simplify to single DATABASE_URL |
| `.gitignore` | Modify | Add `*.db` |
| `docker-compose.yml` | Create | PostgreSQL container (optional) |
| `justfile` | Modify | Update db commands |
| `manage.py` | Modify | Update db commands |

---

### Task 1: Core Infrastructure — base.py, config.py, session.py

**Files:**
- Modify: `app/db/base.py`
- Modify: `app/core/config.py`
- Modify: `app/db/session.py`
- Modify: `app/db/__init__.py`

- [ ] **Step 1: Update `app/db/base.py` — single Base**

```python
from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import declarative_base, declared_attr


class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return Column(DateTime, server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


Base = declarative_base(cls=TimestampMixin)
```

- [ ] **Step 2: Update `app/core/config.py` — single DATABASE_URL**

Replace the 3 database URL fields with:

```python
DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
```

Remove: `USER_DATABASE_URL`, `BUSINESS_DATABASE_URL`, `CONFIG_DATABASE_URL`

Keep: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, and all other fields unchanged.

- [ ] **Step 3: Update `app/db/session.py` — single engine**

```python
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

connect_args = {}
engine_kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)

SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session():
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 4: Update `app/db/__init__.py` — clean exports**

```python
from app.db.base import Base, TimestampMixin
from app.db.repository import BaseRepository
from app.db.session import SessionFactory, engine, get_session

__all__ = [
    "Base",
    "BaseRepository",
    "SessionFactory",
    "TimestampMixin",
    "engine",
    "get_session",
]
```

- [ ] **Step 5: Verify imports don't break**

Run: `python -c "from app.db.base import Base; from app.db.session import engine, get_session; print('OK')"`

- [ ] **Step 6: Commit**

```bash
git add app/db/base.py app/core/config.py app/db/session.py app/db/__init__.py
git commit -m "refactor(db): consolidate to single database infrastructure"
```

---

### Task 2: Update Config Module — Fix Bugs

**Files:**
- Modify: `app/modules/config/models.py`
- Modify: `app/modules/config/router.py`

- [ ] **Step 1: Update `app/modules/config/models.py`**

Change `from app.db.base import BusinessBase` → `from app.db.base import Base`

Change `class SystemConfig(BusinessBase)` → `class SystemConfig(Base)`

- [ ] **Step 2: Update `app/modules/config/router.py`**

Change all `from app.db.session import get_business_session` → `from app.db.session import get_session`

Change all `Depends(get_business_session)` → `Depends(get_session)` (6 occurrences)

- [ ] **Step 3: Commit**

```bash
git add app/modules/config/models.py app/modules/config/router.py
git commit -m "fix(config): use unified session and base, fix wrong session bug"
```

---

### Task 3: Update All Routers — Session Import Rename

**Files:**
- Modify: `app/api/deps.py`
- Modify: `app/modules/users/user_router.py`
- Modify: `app/modules/users/auth_router.py`
- Modify: `app/modules/roles/router.py`
- Modify: `app/modules/orders/router.py`
- Modify: `app/modules/products/router.py`
- Modify: `app/modules/audit/router.py`
- Modify: `app/modules/search/router.py`
- Modify: `app/modules/notifications/router.py`
- Modify: `app/modules/exports/router.py`

- [ ] **Step 1: Update `app/api/deps.py`**

Change `from app.db.session import get_user_session` → `from app.db.session import get_session`

Change `Depends(get_user_session)` → `Depends(get_session)`

- [ ] **Step 2: Update all router files**

For each router file, replace:
- `from app.db.session import get_user_session` → `from app.db.session import get_session`
- `from app.api.deps import ..., get_user_session` → `from app.api.deps import ..., get_session`
- `Depends(get_user_session)` → `Depends(get_session)`

For `app/modules/notifications/router.py` and `app/modules/exports/router.py`:
- `from app.db.session import get_user_session as get_session` → `from app.db.session import get_session`

- [ ] **Step 3: Run tests to verify**

Run: `just test` or `uv run pytest tests -v --cov=app --cov-report=term-missing`

- [ ] **Step 4: Commit**

```bash
git add app/api/deps.py app/modules/*/router.py app/modules/users/*_router.py
git commit -m "refactor(api): unify session imports across all routers"
```

---

### Task 4: Update main.py — Single Engine

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Update imports**

Change:
```python
from app.db.session import UserSessionFactory, business_engine, config_engine, user_engine
```
To:
```python
from app.db.session import SessionFactory, engine
```

- [ ] **Step 2: Update lifespan/shutdown**

Replace:
```python
await user_engine.dispose()
await business_engine.dispose()
await config_engine.dispose()
```
With:
```python
await engine.dispose()
```

- [ ] **Step 3: Update health check**

Replace the 3-database health check with a single check:

```python
@app.get("/health")
async def health_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
```

- [ ] **Step 4: Run tests**

Run: `just test`

- [ ] **Step 5: Commit**

```bash
git add app/main.py
git commit -m "refactor(main): simplify to single database health check and lifecycle"
```

---

### Task 5: Alembic — Single Database Migration

**Files:**
- Modify: `alembic/env.py`
- Delete: `alembic/business_db/env.py`
- Modify: `alembic.ini` (if needed)

- [ ] **Step 1: Update `alembic/env.py`**

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import settings
from app.db.base import Base

# Import all models so they register with Base.metadata
from app.modules.config.models import SystemConfig  # noqa: F401
from app.modules.users.models import User  # noqa: F401
from app.modules.roles.models import Role, Permission  # noqa: F401
from app.modules.users.associations import user_roles  # noqa: F401
from app.modules.roles.associations import role_permissions  # noqa: F401
from app.modules.orders.models import Order, OrderItem  # noqa: F401
from app.modules.products.models import Product  # noqa: F401
from app.modules.audit.models import AuditLog  # noqa: F401
from app.modules.search.models import SearchHistory  # noqa: F401
from app.modules.notifications.models import Notification, NotificationTemplate, NotificationPreference  # noqa: F401
from app.tasks.models import TaskRecord  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 2: Delete `alembic/business_db/env.py`**

```bash
git rm alembic/business_db/env.py
```

- [ ] **Step 3: Generate new initial migration**

```bash
# Delete old migration versions
rm alembic/versions/*.py

# Generate fresh migration
alembic revision --autogenerate -m "initial: single database schema"
```

- [ ] **Step 4: Verify migration**

```bash
# Test with SQLite
DATABASE_URL=sqlite+aiosqlite:///./test_migrate.db alembic upgrade head
rm test_migrate.db
```

- [ ] **Step 5: Commit**

```bash
git add alembic/
git commit -m "refactor(alembic): consolidate to single database migration"
```

---

### Task 6: Dependencies & Config Files

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`
- Modify: `.gitignore`

- [ ] **Step 1: Update `pyproject.toml`**

Remove from dependencies:
- `aiomysql>=0.2.0`
- `aioodbc>=0.4.0`

Keep: `aiosqlite>=0.19.0`, `asyncpg>=0.29.0`

Update project description:
```python
description = "Enterprise FastAPI project with SQLite fallback"
```

Update keywords:
```python
keywords = ["fastapi", "async", "enterprise", "sqlite", "postgresql"]
```

- [ ] **Step 2: Update `.env.example`**

```env
# Application
APP_ENV=development
DEBUG=True

# Security - CHANGE THIS IN PRODUCTION!
SECRET_KEY=change-this-secret-key-in-production

# Database - PostgreSQL (optional, defaults to SQLite if not set)
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/app_db

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]

# Logging
LOG_LEVEL=INFO
```

- [ ] **Step 3: Update `.gitignore`**

Add `*.db` to ignore SQLite database files.

- [ ] **Step 4: Sync dependencies**

```bash
uv sync
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example .gitignore
git commit -m "chore: remove MySQL/SQL Server deps, simplify config"
```

---

### Task 7: Docker & Management

**Files:**
- Create: `docker-compose.yml`
- Modify: `justfile`
- Modify: `manage.py`

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: app_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

- [ ] **Step 2: Update `justfile` database commands**

Update any commands that reference old database URLs or multiple databases.

- [ ] **Step 3: Update `manage.py`**

Update CLI commands that reference old database configuration.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml justfile manage.py
git commit -m "feat: add docker-compose for PostgreSQL, update management commands"
```

---

### Task 8: Update Tests

**Files:**
- Modify: All test files that import `get_user_session` or `get_business_session`
- Modify: Test conftest files with database engine setup

- [ ] **Step 1: Find all test files needing updates**

```bash
grep -r "get_user_session\|get_business_session\|get_config_session\|UserBase\|BusinessBase" tests/
```

- [ ] **Step 2: Update test imports**

Same pattern as routers: `get_user_session` → `get_session`, `UserBase` → `Base`

- [ ] **Step 3: Update test conftest files**

Update any conftest that creates database engines or sessions.

- [ ] **Step 4: Run full test suite**

```bash
just test
```

- [ ] **Step 5: Run linting and type checks**

```bash
just lint
uvx ty check app
```

- [ ] **Step 6: Commit**

```bash
git add tests/
git commit -m "test: update imports for single database refactor"
```

---

### Task 9: Final Verification

- [ ] **Step 1: Test SQLite default (zero config)**

```bash
# Remove DATABASE_URL if set
unset DATABASE_URL  # or remove from .env

# Start app with SQLite
uv run python run.py

# Verify health endpoint
curl http://localhost:8000/health
```

Expected: `{"status": "healthy", "database": "connected"}`

- [ ] **Step 2: Test with PostgreSQL (docker)**

```bash
docker-compose up -d postgres
export DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/app_db
alembic upgrade head
uv run python run.py
```

- [ ] **Step 3: Full test suite**

```bash
just test
just lint
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "refactor: complete single database migration with SQLite fallback"
```
