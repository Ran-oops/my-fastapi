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

    class Config:
        orm_mode = True


class PaginatedResponse(ListResponse[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
