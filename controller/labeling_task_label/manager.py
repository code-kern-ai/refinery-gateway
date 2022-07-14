from submodules.model import LabelingTaskLabel
from submodules.model.business_objects import (
    labeling_task_label,
    labeling_task,
    general,
)
from controller.knowledge_base.util import create_knowledge_base_if_not_existing
from submodules.model.enums import LabelingTaskType


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
