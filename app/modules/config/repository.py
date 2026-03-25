from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import BaseRepository
from app.modules.config.models import SystemConfig
from app.modules.config.schemas import ConfigCreate, ConfigUpdate


class ConfigRepository(BaseRepository[SystemConfig, ConfigCreate, ConfigUpdate]):
    async def get_by_key(self, session: AsyncSession, key: str) -> SystemConfig | None:
        result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
        return result.scalar_one_or_none()


config_repo = ConfigRepository(SystemConfig)
