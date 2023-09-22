import json
import traceback
import os

from controller.transfer.record_transfer_manager import download_file
from submodules.model import UploadTask, enums
from submodules.model.business_objects import project
from controller.upload_task import manager as task_manager
from typing import Dict, Any
from ..util import read_file_to_df
from util import category


def prepare_cognition_import(project_id: str, task: UploadTask) -> None:
    # pre init to ensure we can always append an error
    file_additional_info = __get_blank_file_additional_info()
    project_item = project.get(project_id)
    if not project_item:
        file_additional_info["errors"].append("Can't find project".format(e))
    try:
        tmp_file_name, file_type = download_file(project_id, task)
        df = read_file_to_df(
            file_type,
            tmp_file_name,
            task.user_id,
            task.file_import_options,
            project_id,
        )
        file_additional_info["columns"] = [
            {"name": key, "type": category.infer_category_enum(df, key)}
            for key in df.columns
        ]
    except Exception as e:
        file_additional_info["errors"].append(
            "Error while analyzing file: {}".format(e)
        )
        print(traceback.format_exc(), flush=True)
    finally:
        if os.path.exists(tmp_file_name):
            os.remove(tmp_file_name)
    dumped_info = json.dumps(file_additional_info)
    task_manager.update_task(
        project_id,
        task.id,
        state=enums.UploadStates.PREPARED.value,
        file_additional_info=dumped_info,
    )


def __get_blank_file_additional_info() -> Dict[str, Any]:
    return {
        "columns": [],
        "errors": [],
    }
