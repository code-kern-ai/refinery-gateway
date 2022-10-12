import time
from typing import Dict, Union, Any, List
from graphql_api.types import UserActivityWrapper
from submodules.model.business_objects import user_activity
from util import daemon
import os
from datetime import datetime
import json

BACKUP_FILE_PATH = "user_activity_backup.tmp"
__thread_running = False


def add_user_activity_entry(
    user_id: str, activity: Any, caller_dict: Dict[str, Union[str, int]]
) -> None:
    if isinstance(activity, str):
        activity = {**caller_dict, "activity": activity}
    else:
        activity.update(caller_dict)

    global __thread_running
    if not __thread_running:
        __thread_running = True
        daemon.run(__start_thread_db_write)

    activity_set = [user_id, activity, datetime.now(), False]
    __write_backup_file(activity_set)


def __write_backup_file(content: Any) -> None:
    file = open(BACKUP_FILE_PATH, "a+")
    to_write = [content[0], content[1], "%s" % (content[2]), True]
    to_write = json.dumps(to_write)
    file.write(to_write + "\n")
    file.close()


def __read_backup_file() -> List[Any]:
    if not os.path.exists(BACKUP_FILE_PATH):
        return None
    file = open(BACKUP_FILE_PATH, "r")
    content = file.read()
    content = content.split("\n")
    content = [json.loads(entry) for entry in content if len(entry) > 0]
    for c in content:
        c[2] = datetime.strptime(c[2], "%Y-%m-%d %H:%M:%S.%f")
    return content


def resolve_all_users_activity() -> List[UserActivityWrapper]:
    # here to prevent always load and therfore test error
    from graphql_api.types import UserActivityWrapper, User

    return_values = [
        UserActivityWrapper(
            user=User(id=entry.user_id),
            user_activity=entry.activity_feed,
            warning=entry.has_warning,
            warning_text=entry.warning_text,
        )
        for entry in user_activity.get_all_user_activity()
    ]

    return return_values


def __start_thread_db_write() -> None:
    time.sleep(300)  # only write every 5 min to db to prevent overuse

    if not os.path.exists(BACKUP_FILE_PATH):
        # for multi container environment
        return
    entries_to_add = __read_backup_file()
    if entries_to_add is None:
        return

    user_activity.write_user_activity_safe(entries_to_add)
    # further cleanup
    if os.path.exists(BACKUP_FILE_PATH):
        os.remove(BACKUP_FILE_PATH)
    global __thread_running
    __thread_running = False
