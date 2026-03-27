from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Event:
    """领域事件"""

    event_type: str
    data: dict
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class EventBus:
    """事件总线 - 发布/订阅模式"""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """订阅事件"""
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

    def publish(self, event: Event) -> None:
        """发布事件"""
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            handler(event)

    def clear(self) -> None:
        """清空所有订阅（测试用）"""
        self._subscribers.clear()


eventbus = EventBus()
