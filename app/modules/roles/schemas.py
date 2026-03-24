from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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


class PermissionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Permission name")
    code: str = Field(..., min_length=1, max_length=100, description="Permission code")
    description: str | None = Field(None, max_length=255, description="Permission description")


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100, description="Permission name")
    description: str | None = Field(None, max_length=255, description="Permission description")


class PermissionResponse(PermissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


# 重建模型以支持前向引用
RoleWithPermissions.model_rebuild()
