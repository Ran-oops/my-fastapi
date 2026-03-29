from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.common.pagination import PaginatedResponse, PaginationParams
from app.common.schemas import DataResponse
from app.core.exceptions import NotFoundException
from app.db.session import get_session
from app.modules.config import service as config_service
from app.modules.config.schemas import ConfigCreate, ConfigRead, ConfigUpdate
from app.modules.users.models import User


router = APIRouter()


@router.post("/", response_model=DataResponse[ConfigRead], status_code=status.HTTP_201_CREATED)
async def create_config(
    data: ConfigCreate,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    config = await config_service.create_config(session, data)
    return DataResponse(data=config, message="Config created successfully")


@router.get("/", response_model=PaginatedResponse[ConfigRead])
async def get_configs(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    configs = await config_service.get_configs(session, skip=pagination.skip, limit=pagination.limit)
    total = await config_service.get_configs_count(session)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=configs,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Configs retrieved successfully",
    )


@router.get("/key/{key}", response_model=DataResponse[ConfigRead])
async def get_config_by_key(
    key: str,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    config = await config_service.get_config_by_key(session, key)
    if not config:
        raise NotFoundException(f"Config with key {key} not found")
    return DataResponse(data=config)


@router.get("/{config_id}", response_model=DataResponse[ConfigRead])
async def get_config(
    config_id: int,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    config = await config_service.get_config_by_id(session, config_id)
    if not config:
        raise NotFoundException(f"Config {config_id} not found")
    return DataResponse(data=config)


@router.put("/{config_id}", response_model=DataResponse[ConfigRead])
async def update_config(
    config_id: int,
    data: ConfigUpdate,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    config = await config_service.update_config(session, config_id, data)
    return DataResponse(data=config, message="Config updated successfully")


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    config_id: int,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    await config_service.delete_config(session, config_id)
    return None
