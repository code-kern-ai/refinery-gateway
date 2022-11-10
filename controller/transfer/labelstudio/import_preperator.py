import json
import traceback

from controller.transfer.record_transfer_manager import download_file
from submodules.model import UploadTask, enums
from controller.upload_task import manager as task_manager
from typing import Set, Dict, Any


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
    tasks = set()
    errors = []
    warnings = []
    info = []
    record_count = 0
    has_drafts = False
    has_predictions = False
    try:
        for record in data:
            record_count += 1
            if not has_drafts:
                has_drafts = __check_record_has_values_for(record, "drafts")
            if not has_predictions:
                has_predictions = __check_record_has_values_for(record, "predictions")
            for annotation in record.get("annotations"):
                user_id = annotation.get("completed_by")
                __add_annotation_target(annotation, tasks)

                if user_id in user_id_counts:
                    user_id_counts[user_id] += 1
                else:
                    user_id_counts[user_id] = 1
    except Exception as e:
        errors.append("Error while analyzing file: {}".format(e))
        print(traceback.format_exc(), flush=True)

    if has_drafts:
        warnings.append("Label Studio drafts are not supported.")

    if has_predictions:
        warnings.append("Label Studio predictions are not supported.")

    return {
        "user_ids": [str(user_id) for user_id in user_id_counts],
        "tasks": list(tasks),
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "file_info": {"records": record_count, "annotations": user_id_counts},
    }


def __add_annotation_target(annotation: Dict[str, Any], tasks: Set[str]) -> None:
    target = annotation.get("result")
    if target and len(target) > 0:
        for t in target:
            from_name = t.get("from_name")
            if from_name and from_name not in tasks:
                tasks.add(from_name)


def __check_record_has_values_for(record: Dict[str, Any], key: str) -> bool:
    value = record.get(key)
    if value:
        return True
    return False
    # return key in record and record[key] is not None and len(record[key]) > 0
