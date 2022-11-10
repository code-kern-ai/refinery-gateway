import json
import traceback
import os

from controller.transfer.record_transfer_manager import download_file
from submodules.model import UploadTask, enums
from controller.upload_task import manager as task_manager
from typing import Set, Dict, Any


def prepare_label_studio_import(project_id: str, task: UploadTask) -> None:
    # pre init to ensure we can always append an error
    file_additional_info = __get_blank_file_additional_info()
    try:
        file_path = download_file(project_id, task)
        _, extension = os.path.splitext(file_path)
        if extension == ".json":
            with open(file_path) as file:
                data = json.load(file)
            analyze_file(data, file_additional_info)
        else:
            file_additional_info["errors"].append(f"Unsupported file type {extension}")
    except Exception as e:
        file_additional_info["errors"].append(
            "Error while analyzing file: {}".format(e)
        )
        print(traceback.format_exc(), flush=True)
    dumped_info = json.dumps(file_additional_info)
    task_manager.update_task(
        project_id,
        task.id,
        state=enums.UploadStates.PREPARED.value,
        file_additional_info=dumped_info,
    )


def analyze_file(data: Dict[str, Any], file_additional_info: Dict[str, Any]) -> None:
    user_id_counts = {}
    tasks = set()
    record_count = 0
    ex_drafts = None
    ex_predictions = None
    ex_extraction = None
    ex_multiple_choices = None
    # multiple annotation for a user within the same record/task
    ex_multiple_annotations = None

    for record in data:
        if type(record) is not dict:
            file_additional_info["errors"].append("Import format not recognized")
            break
        record_count += 1
        record_id = record["id"]
        if not ex_drafts and __check_record_has_values_for(record, "drafts"):
            ex_drafts = f"\n\tExample: record {record_id}"
        if not ex_predictions and __check_record_has_values_for(record, "predictions"):
            ex_predictions = f"\n\tExample: record {record_id}"
        if not ex_multiple_annotations and __check_record_has_multi_annotation(record):
            ex_multiple_annotations = f"\n\tExample: record {record_id}"
        for annotation in record["annotations"]:
            annotation_id = annotation["id"]
            if not ex_extraction and __check_annotation_has_extraction(annotation):
                ex_extraction = (
                    f"\n\tExample: record {record_id} - annotation {annotation_id}"
                )
            if not ex_multiple_choices and __check_annotation_has_multiclass(
                annotation
            ):
                ex_multiple_choices = (
                    f"\n\tExample: record {record_id} - annotation {annotation_id}"
                )
            user_id = annotation["completed_by"]
            __add_annotation_target(annotation, tasks)

            if user_id in user_id_counts:
                user_id_counts[user_id] += 1
            else:
                user_id_counts[user_id] = 1

    if ex_drafts:
        file_additional_info["warnings"].append(
            "Label Studio drafts are not supported." + ex_drafts
        )

    if ex_predictions:
        file_additional_info["warnings"].append(
            "Label Studio predictions are not supported." + ex_predictions
        )

    if ex_extraction:
        file_additional_info["errors"].append(
            "Named Entity Recognition / extraction labels are not supported."
            + ex_extraction
        )
    if ex_multiple_choices:
        file_additional_info["errors"].append(
            "Multiple choices for a result set are not supported." + ex_multiple_choices
        )
    if ex_multiple_annotations:
        file_additional_info["errors"].append(
            "Multiple annotations for the same user within the same record\ntargeting the same task are not supported."
            + ex_multiple_annotations
        )

    file_additional_info["user_ids"] = list(user_id_counts.keys())
    file_additional_info["tasks"] = list(tasks)
    file_additional_info["file_info"]["records"] = record_count
    file_additional_info["file_info"]["annotations"] = user_id_counts


def __add_annotation_target(annotation: Dict[str, Any], tasks: Set[str]) -> None:
    tasks |= __get_annotation_targets(annotation)


def __get_annotation_targets(annotation: Dict[str, Any]) -> Set[str]:
    target = annotation.get("result")
    if target and len(target) > 0:
        return {t["from_name"] for t in target if "from_name" in t}
    return {}


def __check_record_has_values_for(record: Dict[str, Any], key: str) -> bool:
    value = record.get(key)
    if value:
        return True
    return False


def __check_record_has_multi_annotation(record: Dict[str, Any]) -> bool:
    annotations = record.get("annotations")
    if not annotations or len(annotations) < 2:
        return False
    lookup = {}
    for annotation in annotations:
        user_id = annotation.get("completed_by")
        if user_id not in lookup:
            lookup[user_id] = {}
        targets = __get_annotation_targets(annotation)
        for target in targets:
            if target not in lookup[user_id]:
                lookup[user_id][target] = 1
            else:
                return True
    return False


def __check_annotation_has_extraction(annotation: Dict[str, Any]) -> bool:
    results = annotation.get("result")
    if not results:
        return False
    for result in results:
        if result.get("type") != "choices":
            return True
    return False


def __check_annotation_has_multiclass(annotation: Dict[str, Any]) -> bool:
    results = annotation.get("result")
    if not results:
        return False
    for result in results:
        if result.get("type") == "choices" and len(result["value"]["choices"]) > 1:
            return True
    return False


def __get_blank_file_additional_info() -> Dict[str, Any]:
    return {
        "user_ids": [],
        "tasks": [],
        "errors": [],
        "warnings": [],
        "info": [],
        "file_info": {"records": 0, "annotations": {}},
    }
