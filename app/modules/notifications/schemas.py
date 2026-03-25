from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    user_id: int
    template: str
    context: dict = Field(default_factory=dict)
