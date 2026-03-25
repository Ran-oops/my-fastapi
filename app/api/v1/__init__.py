from fastapi import APIRouter

from app.modules.users.router import router as users_router
from app.modules.roles.router import router as roles_router

api_router = APIRouter()
api_router.include_router(users_router, tags=["users", "auth"])
api_router.include_router(roles_router, tags=["roles", "permissions"])
