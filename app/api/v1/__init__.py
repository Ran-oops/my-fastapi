from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.config.router import router as config_router
from app.modules.exports.router import router as exports_router
from app.modules.notifications.router import router as notifications_router
from app.modules.orders.router import router as orders_router
from app.modules.products.router import router as products_router
from app.modules.roles.router import router as roles_router
from app.modules.users.auth_router import router as auth_router
from app.modules.users.user_router import router as users_router
from app.modules.search.router import router as search_router
from app.tasks.router import router as tasks_router


api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(roles_router, tags=["roles", "permissions"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(exports_router, prefix="/exports", tags=["exports"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
