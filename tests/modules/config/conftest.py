import uuid

import pytest_asyncio

from app.modules.config import service as config_service
from app.modules.config.schemas import ConfigCreate


@pytest_asyncio.fixture
async def test_config(session):
    unique_key = f"test.key.{uuid.uuid4().hex[:8]}"
    config_in = ConfigCreate(
        key=unique_key,
        value="test_value",
        description="Test configuration",
        is_active=True,
    )
    return await config_service.create_config(session, config_in)


@pytest_asyncio.fixture
async def multiple_configs(session):
    configs = []
    for i in range(5):
        unique_key = f"test.key.{uuid.uuid4().hex[:8]}.{i}"
        config_in = ConfigCreate(
            key=unique_key,
            value=f"value_{i}",
            description=f"Test config {i}",
            is_active=True,
        )
        configs.append(await config_service.create_config(session, config_in))
    return configs
