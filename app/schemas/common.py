from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")


class ResponseBase(BaseModel):
    success: bool = True
    message: str = ""


class DataResponse(ResponseBase, Generic[T]):
    data: T


class ListResponse(ResponseBase, Generic[T]):
    data: List[T]


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 10

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

    class Config:
        orm_mode = True


class PaginatedResponse(ListResponse[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
