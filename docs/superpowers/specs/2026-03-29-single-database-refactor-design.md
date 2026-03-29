# Single Database Refactor Design

Date: 2026-03-29
Status: Ready for Planning

## Executive Summary

Refactor the enterprise FastAPI project from a 3-database architecture (PostgreSQL + SQL Server + MySQL) to a single-database architecture with automatic SQLite fallback. When `DATABASE_URL` is not set, the application uses a local SQLite file with zero configuration. When set to a PostgreSQL URL, it uses PostgreSQL.

## Problem Statement

The current 3-database architecture has significant issues:

1. **Config database (MySQL) is broken**: The config module uses `get_business_session` (SQL Server) instead of `get_config_session` (MySQL). No other module uses the config session. The `ConfigBase` is never used by any model.
2. **Business database models use UserBase**: Orders and Products inherit from `UserBase` (PostgreSQL metadata), not `BusinessBase`. They are effectively already in the PostgreSQL database.
3. **High setup friction**: Developers need PostgreSQL + SQL Server + MySQL running to start the application.
4. **Unnecessary complexity**: 3 engines, 3 session factories, 3 Base classes — but only 1 is actually used.

## Current State Analysis

### Session Usage

| Session | Modules Using It | Call Count |
|---------|-----------------|------------|
| `get_user_session` | users, roles, orders, products, audit, search, notifications, exports | 60+ |
| `get_business_session` | config (BUG: should use config session) | 6 |
| `get_config_session` | None | 0 |

### Base Class Usage

| Base | Models Using It | Count |
|------|----------------|-------|
| `UserBase` | User, Role, Permission, Order, OrderItem, Product, AuditLog, SearchHistory, Notification, NotificationTemplate, NotificationPreference, TaskRecord | 12 |
| `BusinessBase` | SystemConfig | 1 |
| `ConfigBase` | None | 0 |

### Engine Usage

All 3 engines are only used in `main.py` for shutdown disposal and health checks.

## Design

### 1. Configuration Layer

**File: `app/core/config.py`**

Replace 3 database URLs with 1:

```python
DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
```

- Default (unset): SQLite file `./app.db` in project root
- Override: `DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/app_db`

Remove:
- `USER_DATABASE_URL`
- `BUSINESS_DATABASE_URL`
- `CONFIG_DATABASE_URL`

Keep unchanged:
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (out of scope)
- `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, etc.

### 2. Database Layer

**File: `app/db/base.py`**

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

Remove: `BusinessBase`, `ConfigBase`, `ConfigMixin`

**File: `app/db/session.py`**

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

Remove: `user_engine`, `business_engine`, `config_engine`, `UserSessionFactory`, `BusinessSessionFactory`, `ConfigSessionFactory`, `get_user_session`, `get_business_session`, `get_config_session`

### 3. API Layer & Dependency Injection

**File: `app/api/deps.py`**

Change `get_user_session` → `get_session`:

```python
from app.db.session import get_session
```

**All router files** (60+ changes, mostly import renames):

| File | Change |
|------|--------|
| `app/modules/users/user_router.py` | `get_user_session` → `get_session` |
| `app/modules/users/auth_router.py` | `get_user_session` → `get_session` |
| `app/modules/roles/router.py` | `get_user_session` → `get_session` |
| `app/modules/orders/router.py` | `get_user_session` → `get_session` |
| `app/modules/products/router.py` | `get_user_session` → `get_session` |
| `app/modules/audit/router.py` | `get_user_session` → `get_session` |
| `app/modules/search/router.py` | `get_user_session` → `get_session` |
| `app/modules/notifications/router.py` | `get_user_session` → `get_session` |
| `app/modules/exports/router.py` | `get_user_session` → `get_session` |
| `app/modules/config/router.py` | `get_business_session` → `get_session` (BUG FIX) |

**File: `app/db/__init__.py`**

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

### 4. Model Updates

Only 1 model needs a base class change:

**File: `app/modules/config/models.py`**

```python
from app.db.base import Base  # was BusinessBase

class SystemConfig(Base):
    ...
```

All other models already use `UserBase`, which will become `Base`.

### 5. Application Entry Point

**File: `app/main.py`**

```python
from app.db.session import SessionFactory, engine

# Shutdown
@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()

# Health check
async def check_db():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
```

Remove: References to `business_engine`, `config_engine`, multi-db health checks.

### 6. Alembic Migration

- Delete `alembic/business_db/env.py`
- Update `alembic/env.py` to use `settings.DATABASE_URL` and `Base.metadata`
- Generate new initial migration with all tables
- Delete old SQL Server-specific migration files
- Update `alembic.ini` if needed

### 7. Dependencies

**File: `pyproject.toml`**

Remove:
- `aiomysql>=0.2.0`
- `aioodbc>=0.4.0`

Keep:
- `aiosqlite>=0.19.0`
- `asyncpg>=0.29.0`

### 8. Docker (Optional)

**File: `docker-compose.yml`** (new)

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

### 9. Configuration Files

**File: `.env.example`**

```env
# Application
APP_ENV=development
DEBUG=True

# Security
SECRET_KEY=change-this-secret-key-in-production

# Database - PostgreSQL (optional, defaults to SQLite if not set)
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/app_db

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]

# Logging
LOG_LEVEL=INFO
```

**File: `.gitignore`**

Add: `*.db`

### 10. CLI & Management

**File: `manage.py`**

Update database commands to use single `DATABASE_URL`.

**File: `justfile`**

Update `db-upgrade`, `db-migrate` commands for single database.

## Testing Impact

- Test files already use SQLite or mocks — minimal changes needed
- Update any test fixtures that reference `get_user_session` → `get_session`
- Update test conftest files that create database engines

## Migration Path

1. Create new branch
2. Update `base.py` → single `Base`
3. Update `session.py` → single engine + session
4. Update `config.py` → single `DATABASE_URL`
5. Update all routers (import renames)
6. Fix config module bugs
7. Update `main.py`
8. Update Alembic
9. Update dependencies
10. Add `docker-compose.yml`
11. Update `.env.example` and `.gitignore`
12. Generate new initial migration
13. Run full test suite
14. Run linting and type checks

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| SQLite limitations vs PostgreSQL | Low | SQLAlchemy handles dialect differences. Models use standard types only. |
| Breaking existing deployments | Medium | Document migration in CHANGELOG. Old env vars are removed. |
| Alembic migration conflicts | Low | Delete old migrations, generate fresh initial migration. |
| Test failures from import changes | Low | Mechanical rename, easy to fix. |

## Success Criteria

1. `uv run python run.py` works with zero configuration (SQLite)
2. `DATABASE_URL=postgresql+... uv run python run.py` works with PostgreSQL
3. All existing tests pass
4. Linting and type checks pass
5. `docker-compose up` starts PostgreSQL for production-like development
