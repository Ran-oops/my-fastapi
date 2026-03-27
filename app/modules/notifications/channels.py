from abc import ABC, abstractmethod


class NotificationChannel(ABC):
    """通知渠道抽象基类"""

    @abstractmethod
    async def send(self, user_id: int, subject: str | None, body: str) -> tuple[bool, str | None]:
        """
        发送通知

        Returns:
            (success, error_message)
        """
        pass


class InAppChannel(NotificationChannel):
    """站内信渠道 - 仅记录到数据库"""

    async def send(self, user_id: int, subject: str | None, body: str) -> tuple[bool, str | None]:
        return True, None


class EmailChannel(NotificationChannel):
    """邮件渠道 - 占位实现"""

    async def send(self, user_id: int, subject: str | None, body: str) -> tuple[bool, str | None]:
        print(f"[Email] user_id={user_id}, subject={subject}")
        return True, None


class SmsChannel(NotificationChannel):
    """短信渠道 - 预留"""

    async def send(self, user_id: int, subject: str | None, body: str) -> tuple[bool, str | None]:
        return False, "SMS channel not implemented"


CHANNEL_REGISTRY: dict[str, NotificationChannel] = {
    "in_app": InAppChannel(),
    "email": EmailChannel(),
    "sms": SmsChannel(),
}
