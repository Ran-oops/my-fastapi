from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: str | None = Field(None, max_length=255, description="Role description")


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100, description="Role name")
    description: str | None = Field(None, max_length=255, description="Role description")


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None


class RoleWithPermissions(RoleRead):
    permissions: list[PermissionRead] = []


class UserRoleAssign(BaseModel):
    user_id: int = Field(..., description="User ID")
    role_id: int = Field(..., description="Role ID")


class UserRoleResponse(BaseModel):
    user_id: int
    role_id: int
    role_name: str


class PermissionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Permission name")
    code: str = Field(..., min_length=1, max_length=100, description="Permission code")
    description: str | None = Field(None, max_length=255, description="Permission description")


class PermissionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100, description="Permission name")
    description: str | None = Field(None, max_length=255, description="Permission description")


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: str | None


RoleWithPermissions.model_rebuild()
