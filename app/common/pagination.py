from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.common.schemas import ListResponse


T = TypeVar("T")


class PaginationParams(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(ListResponse[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
