from typing import Tuple, Dict, Any, List

from submodules.model import Attribute
from submodules.model.enums import LabelingTaskTarget


def resolve_attribute_information(attribute: Attribute) -> Tuple[str, str]:
    if attribute is None:
        task_target = LabelingTaskTarget.ON_WHOLE_RECORD.value
        attribute_id = None
    else:
        task_target = LabelingTaskTarget.ON_ATTRIBUTE.value
        attribute_id = attribute.id
    return attribute_id, task_target


def infer_labeling_task_name(key: str) -> str:
    return key[key.find("__") + 2 :]


def filter_existing_tasks_and_labels(
    tasks_data: Dict[str, Dict[str, Any]], labels_by_tasks: Dict[str, List[str]]
) -> Tuple[Dict, Dict]:
    creatable_tasks = {}
    creatable_labels = {}
    labels_by_tasks = labels_by_tasks or {}
    for task_name, task_data in tasks_data.items():

        # if task not exist then add for creation
        if task_name not in labels_by_tasks:
            creatable_tasks[task_name] = task_data
            creatable_labels[task_name] = task_data.get("labels",)

        # add labels for creation
        else:
            creatable_labels[task_name] = []
            creatable_labels[task_name].extend(
                [
                    label
                    for label in task_data.get("labels",)
                    if labels_by_tasks.get(task_name)
                    and label not in labels_by_tasks[task_name]
                    and label not in creatable_labels[task_name]
                ]
            )
    return creatable_tasks, creatable_labels
