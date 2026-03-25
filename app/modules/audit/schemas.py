from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditLogCreate(BaseModel):
    user_id: int | None = None
    action: str = Field(..., min_length=1, max_length=20)
    resource_type: str = Field(..., min_length=1, max_length=50)
    resource_id: int = Field(...)
    old_value: str | None = None
    new_value: str | None = None
    ip_address: str | None = Field(None, max_length=45)


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    action: str
    resource_type: str
    resource_id: int
    old_value: str | None
    new_value: str | None
    ip_address: str | None
    created_at: datetime
