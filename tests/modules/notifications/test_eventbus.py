import pytest

from app.core.eventbus import EventBus, Event


@pytest.mark.asyncio
class TestEventBus:
    async def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []

        def handler(event: Event):
            received.append(event)

        bus.subscribe("test.event", handler)
        bus.publish(Event(event_type="test.event", data={"key": "value"}))

        assert len(received) == 1
        assert received[0].event_type == "test.event"
        assert received[0].data == {"key": "value"}

    async def test_multiple_handlers(self):
        bus = EventBus()
        results = []

        bus.subscribe("test.event", lambda e: results.append("handler1"))
        bus.subscribe("test.event", lambda e: results.append("handler2"))
        bus.publish(Event(event_type="test.event", data={}))

        assert results == ["handler1", "handler2"]

    async def test_unsubscribe(self):
        bus = EventBus()
        received = []

        def handler(event: Event):
            received.append(event)

        bus.subscribe("test.event", handler)
        bus.unsubscribe("test.event", handler)
        bus.publish(Event(event_type="test.event", data={}))

        assert len(received) == 0

    async def test_clear(self):
        bus = EventBus()
        received = []

        bus.subscribe("test.event", lambda e: received.append(e))
        bus.clear()
        bus.publish(Event(event_type="test.event", data={}))

        assert len(received) == 0

    async def test_event_has_timestamp(self):
        event = Event(event_type="test.event", data={})
        assert event.timestamp is not None
