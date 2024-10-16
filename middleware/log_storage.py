from typing import List, Dict, Any

import csv
import os
import traceback
from time import sleep
from threading import Lock
from submodules.model import daemon
from fastapi import Request
from datetime import datetime
from submodules.model.enums import AdminLogLevel, try_parse_enum_value
from controller.auth import manager as auth_manager


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
    daemon.run_without_db_token(__persist_log_loop)


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


async def set_request_data(request: Request) -> bytes:
    data = None
    length = request.headers.get("content-length")
    if length and int(length) > 0:
        if request.headers.get("Content-Type") == "application/json":
            data = await request.json()
        else:
            data = await request.body()
    request.state.data = data


async def log_request(request):
    log_request = auth_manager.extract_state_info(request, "log_request")
    log_lvl: AdminLogLevel = try_parse_enum_value(log_request, AdminLogLevel, False)
    # lazy boolean resolution to avoid unnecessary calls
    if (
        not log_lvl
        or not log_lvl.log_me(request.method)
        or (log_lvl == AdminLogLevel.NO_GET and hasattr(request.state, "get_like"))
    ):
        return

    data = None
    if hasattr(request.state, "data"):
        data = request.state.data

    now = datetime.now()
    org_id = auth_manager.extract_state_info(request, "organization_id")
    log_path = f"/logs/admin/{org_id}/{now.strftime('%Y-%m-%d')}.csv"
    log_entry = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "user_id": auth_manager.extract_state_info(request, "user_id"),
        "gateway": "REFINERY",
        "method": str(request.method),
        "path": str(request.url.path),
        "query_params": dict(request.query_params),
        "path_params": dict(request.path_params),  # only after call next possible
        "data": data,
    }
    add_to_persist_queue(log_path, log_entry)
