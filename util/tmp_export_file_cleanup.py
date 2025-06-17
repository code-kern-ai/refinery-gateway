from datetime import datetime, timedelta
from submodules.model.daemon import run_without_db_token
import glob
import os
import traceback
import time

__cleanup_tasks = None


def add_cleanup_task(tmp_filename: str, minutes: int) -> None:
    global __cleanup_tasks
    if __cleanup_tasks is None:
        add_existing_feedback_and_consumption_files_to_cleanup(tmp_filename)
        run_without_db_token(start_cleanup)
    else:
        __cleanup_tasks[tmp_filename] = datetime.now() + timedelta(minutes=minutes)


TMP_PATTERN = [
    "tmp/feedback_*.xlsx",
    "tmp/consumption_*.zip",
    "tmp/consumption_detailed_*.zip",
    "tmp/consumption_summary_*.xlsx",
]


def add_existing_feedback_and_consumption_files_to_cleanup(tmp_filename: str) -> None:
    # failsafe for shutdown before deletion time ran out
    # should only be called for feedback_cleanup_tasks = None
    global __cleanup_tasks
    if __cleanup_tasks is not None:
        raise ValueError("someone didn't read the comment")
    __cleanup_tasks = {}
    for pattern in TMP_PATTERN:
        for filename in glob.glob(pattern):
            minutes = 1  # after a restart they most likely are not valid anymore so we delete them sooner
            if filename == tmp_filename:
                minutes = 60
            __cleanup_tasks[filename] = datetime.now() + timedelta(minutes=minutes)


def start_cleanup() -> None:
    global __cleanup_tasks
    while __cleanup_tasks is not None and len(__cleanup_tasks) > 0:
        try:
            for filename, delete_time in list(__cleanup_tasks.items()):
                if datetime.now() > delete_time:
                    if os.path.isfile(filename):
                        os.remove(filename)
                    del __cleanup_tasks[filename]
        except Exception:
            print("Error in cleanup task", flush=True)
            print(traceback.format_exc(), flush=True)
        finally:
            time.sleep(60)
