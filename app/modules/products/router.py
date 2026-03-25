from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_user_session
from app.common.pagination import PaginatedResponse, PaginationParams
from app.common.schemas import DataResponse
from app.core.exceptions import NotFoundException
from app.modules.products import service as product_service
from app.modules.products.schemas import ProductCreate, ProductRead, ProductUpdate
from app.modules.users.models import User


router = APIRouter()


@router.post("/", response_model=DataResponse[ProductRead], status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    product = await product_service.create_product(session, data)
    return DataResponse(data=product, message="Product created successfully")


@router.get("/", response_model=PaginatedResponse[ProductRead])
async def get_products(
    pagination: PaginationParams = Depends(),
    category: str | None = None,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    if category:
        products = await product_service.get_products_by_category(
            session, category, skip=pagination.skip, limit=pagination.limit
        )
        total = len(products)
    else:
        products = await product_service.get_products(session, skip=pagination.skip, limit=pagination.limit)
        total = await product_service.get_products_count(session)

    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=products,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Products retrieved successfully",
    )


@router.get("/sku/{sku}", response_model=DataResponse[ProductRead])
async def get_product_by_sku(
    sku: str,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    product = await product_service.get_product_by_sku(session, sku)
    if not product:
        raise NotFoundException(f"Product with SKU {sku} not found")
    return DataResponse(data=product)


@router.get("/{product_id}", response_model=DataResponse[ProductRead])
async def get_product(
    product_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    product = await product_service.get_product_by_id(session, product_id)
    if not product:
        raise NotFoundException(f"Product {product_id} not found")
    return DataResponse(data=product)


@router.put("/{product_id}", response_model=DataResponse[ProductRead])
async def update_product(
    product_id: int,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    product = await product_service.update_product(session, product_id, data)
    return DataResponse(data=product, message="Product updated successfully")


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await product_service.delete_product(session, product_id)
    return None
