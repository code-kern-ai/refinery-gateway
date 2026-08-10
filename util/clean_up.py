from submodules.model.business_objects import general, upload_task
import os
import shutil
from submodules.model.daemon import run_without_db_token
from time import sleep
from submodules.model.global_objects import timed_executions


def clean_up_database() -> None:
    general.get_ctx_token()
    try:
        upload_task.remove_all_keys(with_commit=True)
    finally:
        general.remove_and_refresh_session()


def clean_up_disk() -> None:
    """Steps to clean up disk on app start. At the moment deletes only all files in tmp folder"""
    folder = "tmp"
    for filename in os.listdir(folder):
        if filename == ".gitkeep":
            continue
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print("Failed to delete %s. Reason: %s" % (file_path, e))


def start_timed_executions_thread() -> None:
    run_without_db_token(__run_timed_executions)


def __run_timed_executions() -> None:
    sleep(10)  # wait a bit until app is started
    while True:
        try:
            general.get_ctx_token()
            timed_executions.execute_time_key_update(with_commit=True)
        except Exception as e:
            print(f"Error during timed executions: {e}")
        finally:
            general.remove_and_refresh_session()
        sleep(3600)  # run every hour
