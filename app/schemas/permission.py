from pydantic import BaseModel, ConfigDict, Field


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
