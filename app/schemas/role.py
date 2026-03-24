from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field


if TYPE_CHECKING:
    from app.schemas.permission import PermissionResponse


class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: str | None = Field(None, max_length=255, description="Role description")


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100, description="Role name")
    description: str | None = Field(None, max_length=255, description="Role description")


class RoleResponse(RoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class RoleWithPermissions(RoleResponse):
    permissions: list[PermissionResponse] = []


class UserRoleAssign(BaseModel):
    user_id: int = Field(..., description="User ID")
    role_id: int = Field(..., description="Role ID")


class UserRoleResponse(BaseModel):
    user_id: int
    role_id: int
    role_name: str


# Import at runtime for model_rebuild
from app.schemas.permission import PermissionResponse  # noqa: E402


RoleWithPermissions.model_rebuild()
