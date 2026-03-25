from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0)
    category: str | None = Field(None, max_length=100)
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    price: Decimal | None = Field(None, gt=0)
    category: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    description: str | None
    price: Decimal
    category: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
