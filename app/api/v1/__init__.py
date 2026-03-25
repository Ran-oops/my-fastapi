from fastapi import APIRouter

from app.modules.orders.router import router as orders_router
from app.modules.products.router import router as products_router
from app.modules.roles.router import router as roles_router
from app.modules.users.auth_router import router as auth_router
from app.modules.users.user_router import router as users_router


api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(roles_router, tags=["roles", "permissions"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
