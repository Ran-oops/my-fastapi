"""API v2 Router - Next Generation API Version.

This module contains v2 API routes with improved features:
- Enhanced response formats
- Better error handling
- New endpoints for advanced features
- Optimized performance

Migration from v1:
    See docs/migration/v1-to-v2.md for detailed migration guide.
    Breaking changes are documented in docs/changelog/v2.0.0.md
"""

from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.config.router import router as config_router
from app.modules.exports.router import router as exports_router
from app.modules.notifications.router import router as notifications_router
from app.modules.orders.router import router as orders_router
from app.modules.products.router import router as products_router
from app.modules.roles.router import router as roles_router
from app.modules.search.router import router as search_router
from app.modules.users.auth_router import router as auth_router
from app.modules.users.user_router import router as users_router
from app.tasks.router import router as tasks_router

api_router = APIRouter()

# Auth routes - v2 includes OAuth2 enhancements
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"],
)

# User routes - v2 includes profile management improvements
api_router.include_router(
    users_router,
    prefix="/users",
    tags=["users"],
)

# Roles & Permissions routes - v2 includes RBAC v2 features
api_router.include_router(
    roles_router,
    tags=["roles", "permissions"],
)

# Product routes - v2 includes bulk operations
api_router.include_router(
    products_router,
    prefix="/products",
    tags=["products"],
)

# Order routes - v2 includes advanced filtering
api_router.include_router(
    orders_router,
    prefix="/orders",
    tags=["orders"],
)

# Config routes - v2 includes configuration versioning
api_router.include_router(
    config_router,
    prefix="/config",
    tags=["config"],
)

# Audit routes - v2 includes streaming support
api_router.include_router(
    audit_router,
    prefix="/audit",
    tags=["audit"],
)

# Task routes - v2 includes batch operations
api_router.include_router(
    tasks_router,
    prefix="/tasks",
    tags=["tasks"],
)

# Notification routes - v2 includes webhook improvements
api_router.include_router(
    notifications_router,
    prefix="/notifications",
    tags=["notifications"],
)

# Export routes - v2 includes async exports
api_router.include_router(
    exports_router,
    prefix="/exports",
    tags=["exports"],
)

# Search routes - v2 includes faceted search
api_router.include_router(
    search_router,
    prefix="/search",
    tags=["search"],
)
