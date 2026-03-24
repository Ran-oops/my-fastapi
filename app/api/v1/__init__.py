from fastapi import APIRouter

from app.api.v1.endpoints import auth
from app.modules.roles.router import router as roles_router
from app.modules.users.router import router as users_router


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(roles_router, tags=["roles", "permissions"])
