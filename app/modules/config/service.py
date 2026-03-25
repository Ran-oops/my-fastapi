from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.config.models import SystemConfig
from app.modules.config.repository import config_repo
from app.modules.config.schemas import ConfigCreate, ConfigUpdate


async def get_config_by_id(session: AsyncSession, config_id: int) -> SystemConfig | None:
    return await config_repo.get(session, id=config_id)


async def get_config_by_key(session: AsyncSession, key: str) -> SystemConfig | None:
    return await config_repo.get_by_key(session, key=key)


async def get_configs(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[SystemConfig]:
    return await config_repo.get_multi(session, skip=skip, limit=limit)


async def get_configs_count(session: AsyncSession) -> int:
    return await config_repo.count(session)


async def create_config(session: AsyncSession, data: ConfigCreate) -> SystemConfig:
    existing = await config_repo.get_by_key(session, key=data.key)
    if existing:
        raise ConflictException(f"Config with key '{data.key}' already exists")
    return await config_repo.create(session, data=data)


async def update_config(session: AsyncSession, config_id: int, data: ConfigUpdate) -> SystemConfig:
    config = await config_repo.get(session, id=config_id)
    if not config:
        raise NotFoundException(f"Config with id {config_id} not found")
    return await config_repo.update(session, instance=config, data=data)


async def delete_config(session: AsyncSession, config_id: int) -> SystemConfig:
    config = await config_repo.get(session, id=config_id)
    if not config:
        raise NotFoundException(f"Config with id {config_id} not found")
    return await config_repo.delete(session, id=config_id)
