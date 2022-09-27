from submodules.model import LabelingTask
from .util import resolve_attribute_information
from submodules.model.business_objects import labeling_task, general, attribute


def get_labeling_task(project_id: str, labeling_task_id: str) -> LabelingTask:
    return labeling_task.get(project_id, labeling_task_id)


def get_labeling_task_by_name(project_id: str, name: str) -> LabelingTask:
    return labeling_task.get_labeling_task_by_name(project_id, name)


def create_labeling_task(
    project_id: str, name: str, task_type: str, labeling_task_target_id: str
) -> LabelingTask:
    target = attribute.get(project_id, labeling_task_target_id)
    attribute_id, task_target = resolve_attribute_information(target)
    labeling_task_item = labeling_task.create(
        project_id, attribute_id, name, task_target, task_type, with_commit=True
    )
    return labeling_task_item


def update_labeling_task(
    project_id: str,
    task_id: str,
    labeling_task_target_id: str,
    labeling_task_name: str,
    labeling_task_type: str,
) -> None:
    target = attribute.get(project_id, labeling_task_target_id)
    attribute_id, task_target = resolve_attribute_information(target)
    labeling_task.update(
        project_id,
        task_id,
        task_target,
        attribute_id,
        labeling_task_name,
        labeling_task_type,
        with_commit=True,
    )


def delete_labeling_task(project_id: str, labeling_task_id: str) -> None:
    labeling_task.delete(project_id, labeling_task_id, with_commit=True)
