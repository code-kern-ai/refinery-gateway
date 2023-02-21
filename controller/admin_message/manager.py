from typing import Any
from datetime import datetime, timedelta
from submodules.model.business_objects import admin_message


def get_all_admin_messages():
    return admin_message.get_all()


def get_all_active_admin_messages():
    messages = admin_message.get_all_active()

    messages_to_return = []
    now = datetime.now()

    for message in messages:
        if now > message.archive_date:
            admin_message.archive(message.id, None, now, "Archive date reached.")
        else:
            messages_to_return.append(message)

    return messages_to_return


def create_admin_message(text: str, level: str, archive_date: Any, created_by: str):
    now = datetime.now()
    if archive_date < now:
        raise Exception("Archive date not valid")
    admin_message.create(
        text=text,
        level=level,
        archive_date=archive_date,
        created_by=created_by,
    )


def archive_admin_message(message_id: str, archived_by: str, archived_reason: str):
    archive_date = datetime.now()
    admin_message.archive(message_id, archived_by, archive_date, archived_reason)
