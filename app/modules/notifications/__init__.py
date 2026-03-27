from app.modules.notifications.handlers import notification_handler
from app.modules.notifications.service import (
    create_template,
    delete_template,
    get_notification_count,
    get_notifications,
    get_templates,
    mark_all_read,
    mark_notification_read,
    publish_event,
    update_template,
)


__all__ = [
    "create_template",
    "delete_template",
    "get_notification_count",
    "get_notifications",
    "get_templates",
    "mark_all_read",
    "mark_notification_read",
    "notification_handler",
    "publish_event",
    "update_template",
]
