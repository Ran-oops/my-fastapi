# Architecture Refactor & New Module Scaffolding

## Summary

Full structural refactor of the Enterprise FastAPI project to fix architectural issues (god file, circular imports, inconsistent routing, naming) and scaffold 4 new business modules (Products, Orders, Config, Audit) as reference implementations.

## Goals

- Split `shared/db.py` (206 lines, 3 concerns) into focused `db/` package
- Eliminate circular imports between `users/models.py` and `roles/models.py`
- Unify routing: all endpoints in module `router.py`, no scattered `api/v1/endpoints/`
- Adopt consistent, Pythonic naming throughout
- Convert service layer from static-method classes to plain async functions
- Scaffold Products, Orders, Config, Audit modules with new patterns

## Chosen Approach: Layered Module Architecture (Approach A)

Flat structure with clear layer files per module. `shared/` split into `db/` + `common/`. Chosen over Hexagonal (over-engineered for this size) and Package-per-Layer (too deep nesting).

---

## Section 1: Directory Structure

```
app/
├── __init__.py
├── main.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── security.py
│   └── exceptions.py
├── db/                        # From shared/db.py
│   ├── __init__.py
│   ├── base.py                # UserBase, BusinessBase, ConfigBase
│   ├── session.py             # Engines, SessionFactories, get_*_session
│   └── repository.py          # BaseRepository (was CRUDBase)
├── common/                    # From shared/schemas.py
│   ├── __init__.py
│   ├── schemas.py             # DataResponse, ListResponse, ResponseBase
│   └── pagination.py          # PaginationParams, PaginatedResponse
├── api/
│   ├── __init__.py
│   ├── deps.py                # Auth dependencies
│   └── v1/
│       └── __init__.py        # Route registration only
├── modules/
│   ├── __init__.py
│   ├── users/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── associations.py    # user_roles table
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py         # Plain async functions
│   │   └── router.py          # Includes auth endpoints
│   ├── roles/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── associations.py    # role_permissions table
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   ├── products/
│   │   └── (same 6-file pattern)
│   ├── orders/
│   │   └── (same 6-file pattern)
│   ├── config/
│   │   └── (same 6-file pattern)
│   └── audit/
│       └── (same 6-file pattern)
└── cli/                       # Unchanged
```

**Deleted:** `app/modules/shared/`, `app/api/v1/endpoints/`

---

## Section 2: Naming Conventions

| Scope | Before | After | Rationale |
|-------|--------|-------|-----------|
| SQLAlchemy base | `UserDBBase` | `UserBase` | Redundant "DB" removed |
| CRUD base | `CRUDBase` | `BaseRepository` | Standard repository pattern |
| Session factory | `UserSessionLocal` | `UserSessionFactory` | "Factory" describes purpose |
| Session dep | `get_user_db()` | `get_user_session()` | Returns session, not db |
| Repo instance | `user_repository` | `user_repo` | Concise, not confused with class |
| Service | `UserService` + `user_service` | Direct functions | Functions > stateless classes |
| Session param | `db: AsyncSession` | `session: AsyncSession` | Distinguishes from database |
| Input param | `obj_in: CreateSchema` | `data: CreateSchema` | "obj_in" is boilerplate legacy |
| Instance param | `db_obj: Model` | `instance: Model` | "db_obj" has no semantics |
| DB schema | `UserInDB` | `UserDB` | Cleaner |
| Response schema | `UserResponse` | `UserRead` | CRUD symmetry: Create/Read/Update |
| Pydantic base | `UserBase` (schema) | Deleted, fields inline | Avoids name clash with SQLAlchemy |

### Call Comparison

**Before:**
```python
from app.modules.shared.db import get_user_db
from app.modules.users.service import user_service

async def endpoint(db: AsyncSession = Depends(get_user_db)):
    user = await user_service.get_user_by_id(db, user_id)
```

**After:**
```python
from app.db.session import get_user_session
from app.modules.users.service import get_user_by_id

async def endpoint(session: AsyncSession = Depends(get_user_session)):
    user = await get_user_by_id(session, user_id)
```

---

## Section 3: Circular Import Resolution

**Root cause:** `user_roles` table defined in `roles/models.py`, `role_permissions` table in `roles/models.py`, but both modules need to reference each other via relationships.

**Solution:** Extract association tables to dedicated `associations.py` files within each module.

- `users/associations.py` — defines `user_roles` Table
- `roles/associations.py` — defines `role_permissions` Table
- Model files use string-based relationships (`"Role"`, `"User"`) — no cross-imports needed
- All association tables share `UserBase.metadata` — SQLAlchemy resolves at metadata level
- Delete all `from app.modules.X.models import Y  # noqa: E402` lines

---

## Section 4: New Module Definitions

### Products

- **Model:** `Product` with fields: `id`, `name`, `sku` (unique, indexed), `description`, `price` (Decimal), `category`, `is_active`
- **Endpoints:** CRUD + filter by category + lookup by sku
- **DB:** `UserBase`

### Orders

- **Models:** `Order` (id, user_id, status, total_amount) + `OrderItem` (id, order_id, product_id, quantity, unit_price)
- **Relationship:** Order → OrderItems (one-to-many, cascade delete-orphan)
- **Status enum:** pending → confirmed → shipped → completed / cancelled
- **Endpoints:** Create order with items, query orders, status transition, query order items
- **DB:** `UserBase`

### Config (System Configuration)

- **Model:** `SystemConfig` with fields: `id`, `key` (unique, indexed), `value` (Text), `description`, `is_active`
- **Endpoints:** CRUD + lookup by key
- **DB:** `BusinessBase`

### Audit (Audit Log)

- **Model:** `AuditLog` with fields: `id`, `user_id`, `action`, `resource_type`, `resource_id`, `old_value` (JSON), `new_value` (JSON), `ip_address`
- **Endpoints:** Read-only query + filter by user/resource
- **DB:** `UserBase`

Each module follows: `models.py` / `associations.py` (if needed) / `schemas.py` / `repository.py` / `service.py` (functions) / `router.py`

---

## Section 5: API Routing

All endpoints belong in module `router.py`. `api/v1/__init__.py` only registers routers:

```python
api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(roles_router, prefix="/roles", tags=["roles"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
```

Auth endpoints (register, login) live in `users/router.py` under `/auth/` prefix.

**Deleted:** `app/api/v1/endpoints/` directory and `auth.py`

---

## Section 6: db/ Module Split

`shared/db.py` (206 lines, 3 concerns) → 3 focused files:

### db/base.py
- `TimestampMixin` (created_at, updated_at declared_attr)
- `ConfigMixin` (empty, for config db)
- `UserBase = declarative_base(cls=TimestampMixin)`
- `BusinessBase = declarative_base(cls=TimestampMixin)`
- `ConfigBase = declarative_base(cls=ConfigMixin)`

### db/session.py
- `user_engine`, `business_engine`, `config_engine`
- `UserSessionFactory`, `BusinessSessionFactory`, `ConfigSessionFactory`
- `get_user_session()`, `get_business_session()`, `get_config_session()` async generators

### db/repository.py
- `BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType]`
- Methods: `get`, `get_multi`, `count`, `create`, `update`, `delete`
- Parameter names: `session`, `data`, `instance`

### db/\_\_init\_\_.py
Re-exports all public symbols for convenience.

**Deleted:** `app/modules/shared/` directory

---

## Section 7: Test Structure

Tests mirror `app/` structure:

```
tests/
├── conftest.py
├── modules/
│   ├── users/
│   │   ├── test_user_api.py
│   │   └── test_user_service.py
│   ├── roles/
│   │   ├── test_role_api.py
│   │   └── test_role_service.py
│   ├── products/
│   ├── orders/
│   ├── config/
│   └── audit/
├── core/
│   ├── test_security.py
│   └── test_exceptions.py
└── db/
    └── test_repository.py
```

**Deleted:** `tests/test_api/`, `tests/test_services/`

---

## Section 8: Implementation Order

Each step verified with `just lint` + `just test` before proceeding.

| Step | Action | Risk |
|------|--------|------|
| 1 | Split `shared/db.py` → `db/` (base, session, repository), update imports | Low |
| 2 | Split `shared/schemas.py` → `common/` (schemas, pagination), update imports | Low |
| 3 | Resolve circular imports: extract association tables to `associations.py` | Medium |
| 4 | Rename: `CRUDBase`→`BaseRepository`, param names, instance names | Low |
| 5 | Convert services to functions: delete `UserService`/`RoleService` classes | Medium |
| 6 | Route restructure: auth into users, delete `api/v1/endpoints/` | Low |
| 7 | Delete `shared/` directory | Low |
| 8 | Restructure tests, migrate existing tests | Low |
| 9 | Scaffold Products module (reference implementation) | Low |
| 10 | Scaffold Orders module | Low |
| 11 | Scaffold Config module | Low |
| 12 | Scaffold Audit module | Low |
| 13 | Full lint + test verification | — |

---

## Verification

- All existing tests pass after each step (1-8)
- New module tests pass after each step (9-12)
- `just lint` clean
- `just test` all green
- No circular imports (verified via `python -c "from app.main import app"`)
- API docs render correctly at `/api/v1/docs`
