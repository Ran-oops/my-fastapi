import pytest

from app.modules.notifications.channels import (
    InAppChannel,
    EmailChannel,
    SmsChannel,
    CHANNEL_REGISTRY,
)


@pytest.mark.asyncio
class TestChannels:
    async def test_in_app_channel_send(self):
        channel = InAppChannel()
        success, error = await channel.send(1, "Test Subject", "Test Body")
        assert success is True
        assert error is None

    async def test_email_channel_send(self):
        channel = EmailChannel()
        success, error = await channel.send(1, "Test Subject", "Test Body")
        assert success is True
        assert error is None

    async def test_sms_channel_not_implemented(self):
        channel = SmsChannel()
        success, error = await channel.send(1, "Test", "Test")
        assert success is False
        assert "not implemented" in error

    async def test_channel_registry_contains_all_channels(self):
        assert "in_app" in CHANNEL_REGISTRY
        assert "email" in CHANNEL_REGISTRY
        assert "sms" in CHANNEL_REGISTRY

    async def test_channel_registry_returns_correct_types(self):
        assert isinstance(CHANNEL_REGISTRY["in_app"], InAppChannel)
        assert isinstance(CHANNEL_REGISTRY["email"], EmailChannel)
        assert isinstance(CHANNEL_REGISTRY["sms"], SmsChannel)
