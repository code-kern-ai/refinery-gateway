from typing import List, Dict, Any

import csv
import os
import traceback
from time import sleep
from threading import Lock
from util import daemon
from fastapi import Request


__not_yet_persisted = {}  # {log_path: List[Dict[str,Any]]}
__THREAD_LOCK = Lock()


# not really an interval as the thread sleeps for the whole duration
# however, this is ideal here as we wouldn't want to stack up persisting tasks if lock files are present
__PERSIST_INTERVAL = 1  # minutes


def add_to_persist_queue(log_path: str, data: Dict[str, Any]):
    global __not_yet_persisted
    with __THREAD_LOCK:
        if log_path not in __not_yet_persisted:
            __not_yet_persisted[log_path] = []

        __not_yet_persisted[log_path].append(data)


def start_persist_thread():
    daemon.run(__persist_log_loop)


def __persist_log_loop():
    global __not_yet_persisted
    while True:
        sleep(__PERSIST_INTERVAL * 60)
        if len(__not_yet_persisted) > 0:
            try:
                with __THREAD_LOCK:
                    data = __not_yet_persisted
                    __not_yet_persisted = {}

                __persist_log(data)
            except Exception:
                print(traceback.format_exc(), flush=True)


def __persist_log(data: Dict[str, List[Dict[str, Any]]]) -> None:
    for log_path in data.keys():
        if len(data[log_path]) == 0:
            continue
        if not os.path.exists(os.path.dirname(log_path)):
            os.makedirs(os.path.dirname(log_path))
        if os.path.isfile(log_path + ".lock"):
            i = 0
            while os.path.isfile(log_path + ".lock") and i < 60:
                sleep(1)
                i += 1
            if i == 60:
                raise Exception("Could not acquire lock for log file")
        with open(log_path + ".lock", "w") as f:
            pass
        try:
            if not os.path.isfile(log_path):
                with open(log_path, "w", newline="") as f:
                    w = csv.DictWriter(f, data[log_path][0].keys())
                    w.writeheader()
                    __write_log_entries(w, data[log_path])
            else:
                with open(log_path, "a", newline="") as f:
                    w = csv.DictWriter(f, data[log_path][0].keys())
                    __write_log_entries(w, data[log_path])
        finally:
            os.remove(log_path + ".lock")


def __write_log_entries(
    writer: csv.DictWriter, log_entries: List[Dict[str, Any]]
) -> None:
    for log_entry in log_entries:
        writer.writerow(log_entry)


def extend_state_get_like(request: Request):
    request.state.get_like = True
