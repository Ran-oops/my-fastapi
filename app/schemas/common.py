from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ResponseBase(BaseModel):
    success: bool = True
    message: str = ""


class DataResponse(ResponseBase, Generic[T]):
    data: T


class ListResponse(ResponseBase, Generic[T]):
    data: list[T]


class PaginationParams(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int = 1
    page_size: int = 10

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
