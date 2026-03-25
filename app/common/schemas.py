from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseBase(BaseModel):
    success: bool = True
    message: str = ""


class DataResponse[T](ResponseBase):
    data: T


class ListResponse[T](ResponseBase):
    data: list[T]
