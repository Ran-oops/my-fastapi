import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.config import service as config_service
from app.modules.config.schemas import ConfigCreate, ConfigUpdate
from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestConfigServiceCreate:
    async def test_create_config_success(self, session: AsyncSession):
        unique_key = f"test.key.{uuid.uuid4().hex[:8]}"
        config_in = ConfigCreate(
            key=unique_key,
            value="test_value",
            description="Test configuration",
            is_active=True,
        )
        result = await config_service.create_config(session, config_in)
        assert result.id is not None
        assert result.key == unique_key
        assert result.value == "test_value"
        assert result.description == "Test configuration"
        assert result.is_active is True

    async def test_create_config_duplicate_key(self, session: AsyncSession):
        unique_key = f"duplicate.key.{uuid.uuid4().hex[:8]}"
        config_in = ConfigCreate(key=unique_key, value="first_value")
        await config_service.create_config(session, config_in)

        with pytest.raises(ConflictException) as exc_info:
            await config_service.create_config(session, ConfigCreate(key=unique_key, value="second_value"))
        assert "already exists" in str(exc_info.value)

    async def test_create_config_minimal(self, session: AsyncSession):
        unique_key = f"minimal.key.{uuid.uuid4().hex[:8]}"
        config_in = ConfigCreate(key=unique_key, value="minimal_value")
        result = await config_service.create_config(session, config_in)
        assert result.id is not None
        assert result.key == unique_key
        assert result.value == "minimal_value"
        assert result.description is None
        assert result.is_active is True


@pytest.mark.asyncio
class TestConfigServiceGet:
    async def test_get_config_by_id_found(self, session: AsyncSession, test_config):
        result = await config_service.get_config_by_id(session, test_config.id)
        assert result is not None
        assert result.id == test_config.id
        assert result.key == test_config.key

    async def test_get_config_by_id_not_found(self, session: AsyncSession):
        result = await config_service.get_config_by_id(session, NONEXISTENT_ID)
        assert result is None

    async def test_get_config_by_key_found(self, session: AsyncSession, test_config):
        result = await config_service.get_config_by_key(session, test_config.key)
        assert result is not None
        assert result.key == test_config.key

    async def test_get_config_by_key_not_found(self, session: AsyncSession):
        result = await config_service.get_config_by_key(session, "nonexistent.key")
        assert result is None


@pytest.mark.asyncio
class TestConfigServiceList:
    async def test_get_configs_pagination(self, session: AsyncSession, multiple_configs):
        page1 = await config_service.get_configs(session, skip=0, limit=2)
        page2 = await config_service.get_configs(session, skip=2, limit=2)
        assert len(page1) <= 2
        assert len(page2) <= 2
        if len(page1) == 2 and len(page2) > 0:
            assert page1[0].id != page2[0].id

    async def test_get_configs_count(self, session: AsyncSession, multiple_configs):
        count = await config_service.get_configs_count(session)
        assert count >= 5


@pytest.mark.asyncio
class TestConfigServiceUpdate:
    async def test_update_config_success(self, session: AsyncSession):
        unique_key = f"update.key.{uuid.uuid4().hex[:8]}"
        config_in = ConfigCreate(key=unique_key, value="original_value")
        config = await config_service.create_config(session, config_in)

        update_in = ConfigUpdate(value="updated_value", description="Updated description")
        result = await config_service.update_config(session, config.id, update_in)
        assert result.value == "updated_value"
        assert result.description == "Updated description"

    async def test_update_config_partial(self, session: AsyncSession):
        unique_key = f"partial.key.{uuid.uuid4().hex[:8]}"
        config_in = ConfigCreate(key=unique_key, value="original_value", description="Original")
        config = await config_service.create_config(session, config_in)

        update_in = ConfigUpdate(value="new_value")
        result = await config_service.update_config(session, config.id, update_in)
        assert result.value == "new_value"
        assert result.description == "Original"

    async def test_update_config_not_found(self, session: AsyncSession):
        update_in = ConfigUpdate(value="new_value")
        with pytest.raises(NotFoundException) as exc_info:
            await config_service.update_config(session, NONEXISTENT_ID, update_in)
        assert "not found" in str(exc_info.value)


@pytest.mark.asyncio
class TestConfigServiceDelete:
    async def test_delete_config_success(self, session: AsyncSession):
        unique_key = f"delete.key.{uuid.uuid4().hex[:8]}"
        config_in = ConfigCreate(key=unique_key, value="to_delete")
        config = await config_service.create_config(session, config_in)

        result = await config_service.delete_config(session, config.id)
        assert result.id == config.id

        deleted = await config_service.get_config_by_id(session, config.id)
        assert deleted is None

    async def test_delete_config_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundException) as exc_info:
            await config_service.delete_config(session, NONEXISTENT_ID)
        assert "not found" in str(exc_info.value)
