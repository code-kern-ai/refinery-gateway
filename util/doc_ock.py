import os
import traceback
from controller.misc import config_service
from submodules.model import models, events
from util import daemon, service_requests
from controller.auth import kratos
from util.user_activity import add_user_activity_entry

BASE_URI = os.getenv("DOC_OCK")


def register_user(user: models.User):
    url = f"{BASE_URI}/register_user/{user.id}"
    user_obj = kratos.resolve_user_name_by_id(user.id)
    user_data = {
        "first_name": user_obj["first"] if user_obj else "UNKNOWN User ID",
        "last_name": user_obj["last"] if user_obj else "UNKNOWN User ID",
        "email": kratos.resolve_user_mail_by_id(user.id),
        "organization": user.organization.name,
    }
    return service_requests.post_call_or_raise(url, user_data)


def post_event(user: models.User, event: events.Event):
    daemon.run(__post_thread, user, event)

def __post_thread(user: models.User, event: events.Event):
    try:
        url = f"{BASE_URI}/track/{user.id}/{event.event_name()}"
        event.IsManaged = config_service.get_config_value("is_managed")
        add_user_activity_entry(
            str(user.id), {"eventName": event.event_name(), **event.__dict__}
        )
        service_requests.post_call_or_raise(url, event.__dict__)
    except Exception:
        print(traceback.format_exc(), flush=True)
