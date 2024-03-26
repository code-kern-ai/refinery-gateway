from submodules.model.business_objects.notification import get_notifications_by_user_id
from submodules.model.models import Notification


def get_notification(user_id: str) -> Notification:
    return get_notifications_by_user_id(user_id)
