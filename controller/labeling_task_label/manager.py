from submodules.model import LabelingTaskLabel
from submodules.model.business_objects import (
    labeling_task_label,
    labeling_task,
    general,
    knowledge_base,
    information_source,
    record_label_association,
)
from controller.knowledge_base.util import create_knowledge_base_if_not_existing
from submodules.model.enums import LabelingTaskType
from submodules.model import enums
from util import notification


from typing import List, Any, Dict
import re


def get_label(project_id: str, label_id: str) -> LabelingTaskLabel:
    return labeling_task_label.get(project_id, label_id)


def update_label_color(project_id: str, label_id: str, color: str) -> None:
    label = get_label(project_id, label_id)
    label.color = color
    general.commit()


def update_label_hotkey(project_id: str, label_id: str, hotkey: str) -> None:
    label = get_label(project_id, label_id)
    label.hotkey = hotkey
    general.commit()


def update_label_name(project_id: str, label_id: str, new_name: str) -> None:
    label = get_label(project_id, label_id)
    label.name = new_name
    general.commit()


def handle_label_rename_warning(project_id: str, warning_data: Dict[str, str]) -> None:
    if warning_data["key"] == enums.CommentCategory.KNOWLEDGE_BASE.value:
        knowledge_base_item = knowledge_base.get_by_name(
            project_id, warning_data["old"]
        )
        knowledge_base_item.name = warning_data["new"]
        general.commit()

        notification.send_organization_update(
            project_id, f"knowledge_base_updated:{str(knowledge_base_item.id)}"
        )
    elif warning_data["key"] == enums.CommentCategory.HEURISTIC.value:
        information_source_item = information_source.get(project_id, warning_data["id"])
        information_source_item.source_code = warning_data["new"]
        general.commit()

        notification.send_organization_update(
            project_id, f"information_source_updated:{str(information_source_item.id)}"
        )


def create_label(
    project_id: str, name: str, labeling_task_id: str, label_color: str
) -> LabelingTaskLabel:
    task = labeling_task.get(project_id, labeling_task_id)
    label = labeling_task_label.create(project_id, name, labeling_task_id, label_color)

    if task.task_type == LabelingTaskType.INFORMATION_EXTRACTION.value:
        create_knowledge_base_if_not_existing(name, project_id)

    general.commit()
    return label


def delete_label(project_id: str, label_id: str) -> None:
    labeling_task_label.delete(project_id, label_id, with_commit=True)


def check_rename_label(project_id: str, label_id: str, new_name: str) -> List[Any]:
    label_item = labeling_task_label.get(project_id, label_id)
    if not label_item or label_item.name == new_name:
        return []
    return __get_change_dict(project_id, label_item, new_name)


def __get_change_dict(
    project_id: str, label: LabelingTaskLabel, new_name: str
) -> Dict[str, str]:
    return_values = {
        "errors": __check_errors_label_rename(project_id, label, new_name),
        "warnings": __check_warning_label_rename(project_id, label, new_name),
        "infos": [],
    }
    __check_label_rename_knowledge_base(project_id, label, new_name, return_values)
    if len(return_values["errors"]) == 0 and len(return_values["warnings"]) == 0:
        return_values["infos"].append(__get_msg_dict("No issues detected"))
    return return_values


def __get_msg_dict(msg: str) -> Dict[str, str]:
    return {"msg": msg}


def __check_errors_label_rename(
    project_id: str, label: LabelingTaskLabel, new_name: str
) -> List[Dict[str, Any]]:
    append_me = []
    existing_with_name = labeling_task_label.get_by_name(
        project_id, str(label.labeling_task_id), new_name
    )
    if existing_with_name:
        append_me.append(__get_msg_dict("Label with name already exists"))
    return append_me


def __check_warning_label_rename(
    project_id: str, label: LabelingTaskLabel, new_name: str
) -> List[Dict[str, Any]]:
    append_me = []

    information_sources = information_source.get_all(project_id)
    for information_source_item in information_sources:
        current_code = information_source_item.source_code
        new_code = re.sub(r"\b%s\b" % label.name, new_name, current_code)
        if current_code != new_code:
            entry = __get_msg_dict(
                "Information source with matching word was detected."
            )
            entry["key"] = enums.CommentCategory.HEURISTIC.value
            entry["id"] = str(information_source_item.id)
            entry["old"] = current_code
            entry["new"] = new_code
            entry["old_name"] = label.name
            entry["new_name"] = new_name
            append_me.append(entry)

    return append_me


def __check_label_rename_knowledge_base(
    project_id: str, label: LabelingTaskLabel, new_name: str, append_to
) -> None:
    knowledge_base_item = knowledge_base.get_by_name(project_id, label.name)
    if knowledge_base_item:
        entry = __get_msg_dict("Lookup list with same name as label exists.")
        entry["key"] = enums.CommentCategory.KNOWLEDGE_BASE.value
        entry["old"] = knowledge_base_item.name
        entry["new"] = new_name
        knowledge_base_item_new = knowledge_base.get_by_name(project_id, new_name)
        if knowledge_base_item_new:
            entry["msg"] += "\n\tNew label name however, already exists as lookup list."
            append_to["errors"].append(entry)
        else:
            append_to["warnings"].append(entry)
