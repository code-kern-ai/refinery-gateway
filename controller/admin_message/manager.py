from typing import Any, List
from datetime import datetime
from submodules.model.business_objects import admin_message, general
from submodules.model.models import AdminMessage
from util.notification import send_global_update_for_all_organizations


def get_all_admin_messages() -> List[AdminMessage]:
    get_and_check_all_active_admin_messages()
    return admin_message.get_all()


def get_and_check_all_active_admin_messages() -> List[AdminMessage]:
    messages = admin_message.get_all_active()
    messages_to_return = []
    now = datetime.now()
    message_archived = False
    for message in messages:
        if now > message.archive_date:
            admin_message.archive(
                message.id, None, now, "Archive date reached.", with_commit=False
            )
            message_archived = True
        else:
            messages_to_return.append(message)
        if message_archived:
            general.commit()
            send_global_update_for_all_organizations("admin_message")

    return messages_to_return


def create_admin_message(
    text: str, level: str, archive_date: datetime, created_by: str
) -> AdminMessage:
    now = datetime.now().astimezone(archive_date.tzinfo)

    if archive_date < now:
        raise ValueError("Archive date not valid")
    return admin_message.create(
        text=text,
        level=level,
        archive_date=archive_date,
        created_by=created_by,
        with_commit=True,
    )


def archive_admin_message(
    message_id: str, archived_by: str, archived_reason: str
) -> None:
    archive_date = datetime.now()
    admin_message.archive(
        message_id, archived_by, archive_date, archived_reason, with_commit=True
    )
