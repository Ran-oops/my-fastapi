from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_user_session
from app.common.pagination import PaginatedResponse, PaginationParams
from app.common.schemas import DataResponse
from app.core.exceptions import NotFoundException
from app.modules.orders import service as order_service
from app.modules.orders.models import OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderRead, OrderUpdate, OrderWithItems
from app.modules.users.models import User


router = APIRouter()


@router.post("/", response_model=DataResponse[OrderRead], status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    order = await order_service.create_order(session, data)
    return DataResponse(data=order, message="Order created successfully")


@router.get("/", response_model=PaginatedResponse[OrderRead])
async def get_orders(
    pagination: PaginationParams = Depends(),
    user_id: int | None = None,
    status: OrderStatus | None = None,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    if user_id:
        orders = await order_service.get_orders_by_user(session, user_id, skip=pagination.skip, limit=pagination.limit)
        total = len(orders)
    elif status:
        orders = await order_service.get_orders_by_status(session, status, skip=pagination.skip, limit=pagination.limit)
        total = len(orders)
    else:
        orders = await order_service.get_orders(session, skip=pagination.skip, limit=pagination.limit)
        total = await order_service.get_orders_count(session)

    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=orders,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Orders retrieved successfully",
    )


@router.get("/my", response_model=PaginatedResponse[OrderRead])
async def get_my_orders(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_user_session),
    current_user: User = Depends(get_current_user),
):
    orders = await order_service.get_orders_by_user(
        session, current_user.id, skip=pagination.skip, limit=pagination.limit
    )
    total = len(orders)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=orders,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Orders retrieved successfully",
    )


@router.get("/{order_id}", response_model=DataResponse[OrderWithItems])
async def get_order(
    order_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_user),
):
    order = await order_service.get_order_with_items(session, order_id)
    if not order:
        raise NotFoundException(f"Order {order_id} not found")
    return DataResponse(data=order)


@router.put("/{order_id}", response_model=DataResponse[OrderRead])
async def update_order(
    order_id: int,
    data: OrderUpdate,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    order = await order_service.update_order_status(session, order_id, data)
    return DataResponse(data=order, message="Order updated successfully")


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    session: AsyncSession = Depends(get_user_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await order_service.delete_order(session, order_id)
    return None
