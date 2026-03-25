from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConfigCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1)
    description: str | None = Field(None, max_length=255)
    is_active: bool = True


class ConfigUpdate(BaseModel):
    value: str | None = Field(None, min_length=1)
    description: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class ConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    value: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
