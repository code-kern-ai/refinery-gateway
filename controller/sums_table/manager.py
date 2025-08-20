from time import sleep
from datetime import timedelta, datetime
from submodules.model import daemon
from submodules.model.enums import AdminQueries
from submodules.model.global_objects import sums_table as sums_table_db_go
from submodules.model.business_objects import general
import traceback


NEXT_EXEC = {}
SUM_TABLE_TASKS = {
    AdminQueries.PRIVATEMODE_USE_OVER_TIME.value: timedelta(days=1),
}
SUM_TABLE_REMOVES = {
    AdminQueries.PRIVATEMODE_USE_OVER_TIME.value: timedelta(days=90),
}


def start_sums_table_thread() -> None:
    __init_next_exec()
    daemon.run_without_db_token(__sum_table_thread)


def __sum_table_thread() -> None:
    global NEXT_EXEC, SUM_TABLE_TASKS
    while True:
        sleep(5)
        now = datetime.now()
        # collect only keys that are due
        to_run = [
            (k, delta)
            for k, delta in SUM_TABLE_TASKS.items()
            if now >= NEXT_EXEC.get(k, datetime.min)
        ]

        if not to_run:
            continue

        if to_run:
            try:
                general.get_ctx_token()
                for key, delta in to_run:
                    data = __get_sum_data_by_key(key)
                    if not data:
                        raise ValueError("No sum data found")
                    sums_table_db_go.create(sum_key=key, data=data, with_commit=True)
                    NEXT_EXEC[key] = now + delta
                _cleanup_old_entries()  # only if something run we clean so we dont do this to often
            except Exception:
                print(traceback.format_exc(), flush=True)
            finally:
                general.remove_and_refresh_session()


def __init_next_exec() -> None:
    global NEXT_EXEC

    for key, delta in SUM_TABLE_TASKS.items():
        NEXT_EXEC[key] = sums_table_db_go.get_last_execution_by_key(key)
        if NEXT_EXEC[key] is None:
            NEXT_EXEC[key] = datetime.now()
        else:
            NEXT_EXEC[key] = NEXT_EXEC[key] + delta


def __get_sum_data_by_key(sum_key: str) -> dict:
    if sum_key == AdminQueries.PRIVATEMODE_USE_OVER_TIME.value:
        return sums_table_db_go.get_privatemode_sum_snapshot()
    return None


def _cleanup_old_entries() -> None:
    global NEXT_EXEC
    for key, delta in SUM_TABLE_REMOVES.items():
        sums_table_db_go.clean_old_entries(key, delta)
