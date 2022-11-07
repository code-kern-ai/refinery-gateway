import json

from controller.transfer.record_transfer_manager import download_file
from submodules.model import UploadTask, enums
from controller.upload_task import manager as task_manager



def prepare_label_studio_import(project_id: str, task: UploadTask) -> None:
    file_path = download_file(project_id, task)
    with open(file_path) as file:
        data = json.load(file)
        file_additional_info = analyze_file(data)
        dumped_info = json.dumps(file_additional_info)
        task_manager.update_task(
            project_id,
            task.id,
            state=enums.UploadStates.PREPARED.value,
            file_additional_info=dumped_info,
        )


def analyze_file(data):
    user_id_counts = {}
    errors = []
    warnings = []
    info = []
    record_count = 0
    for record in data:
        record_count += 1
        for annotation in record.get("annotations"):
            user_id = annotation.get("completed_by")

            if user_id in user_id_counts:
                user_id_counts[user_id] += 1
            else:
                user_id_counts[user_id] = 1

    return {
        "user_ids": [str(user_id) for user_id in user_id_counts],
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "file_info": {"records": record_count, "annotations": user_id_counts},
    }
