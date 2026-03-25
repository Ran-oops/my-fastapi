from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_name: str
    celery_task_id: str | None
    status: str
    params: dict | None
    error: str | None
    retry_count: int
    scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
