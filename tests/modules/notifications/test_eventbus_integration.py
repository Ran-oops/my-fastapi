import pytest

from app.core.eventbus import Event, EventBus
from app.core.events import ORDER_CONFIRMED, ORDER_SHIPPED


@pytest.mark.asyncio
class TestEventBusIntegration:
    async def test_subscribe_multiple_event_types(self):
        bus = EventBus()
        received = []

        def handler1(event: Event):
            received.append(("handler1", event.event_type))

        def handler2(event: Event):
            received.append(("handler2", event.event_type))

        bus.subscribe(ORDER_CONFIRMED, handler1)
        bus.subscribe(ORDER_SHIPPED, handler2)

        bus.publish(Event(event_type=ORDER_CONFIRMED, data={"order_id": 1}))
        bus.publish(Event(event_type=ORDER_SHIPPED, data={"order_id": 2}))

        assert len(received) == 2
        assert received[0] == ("handler1", ORDER_CONFIRMED)
        assert received[1] == ("handler2", ORDER_SHIPPED)

    async def test_handler_can_publish_new_event(self):
        bus = EventBus()
        events = []

        def outer_handler(event: Event):
            events.append(event.event_type)
            bus.publish(Event(event_type="inner.event", data={}))

        def inner_handler(event: Event):
            events.append(event.event_type)

        bus.subscribe("outer.event", outer_handler)
        bus.subscribe("inner.event", inner_handler)

        bus.publish(Event(event_type="outer.event", data={}))

        assert events == ["outer.event", "inner.event"]

    async def test_exception_in_handler_does_not_stop_others(self):
        bus = EventBus()
        results = []

        def failing_handler(event: Event):
            raise ValueError("Handler failed")

        def success_handler(event: Event):
            results.append("success")

        bus.subscribe("test.event", failing_handler)
        bus.subscribe("test.event", success_handler)

        with pytest.raises(ValueError):
            bus.publish(Event(event_type="test.event", data={}))

    async def test_event_data_preserved(self):
        bus = EventBus()
        received_data = None

        def handler(event: Event):
            nonlocal received_data
            received_data = event.data

        bus.subscribe("test.event", handler)
        bus.publish(Event(event_type="test.event", data={"key": "value", "nested": {"a": 1}}))

        assert received_data == {"key": "value", "nested": {"a": 1}}

    async def test_event_timestamp_auto_generated(self):
        event1 = Event(event_type="test", data={})
        event2 = Event(event_type="test", data={})

        assert event1.timestamp is not None
        assert event2.timestamp is not None
