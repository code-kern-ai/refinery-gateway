from typing import List
from controller.information_source.util import resolve_source_return_type
from submodules.model import InformationSource, LabelingTask
from submodules.model.business_objects import general, labeling_task, information_source


def get_information_source(project_id: str, source_id: str) -> InformationSource:
    return information_source.get(project_id, source_id)


def get_all_information_sources(project_id: str) -> List[InformationSource]:
    return information_source.get_all(project_id)


def get_overview_data(project_id: str) -> str:
    return information_source.get_overview_data(project_id)


def create_information_source(
    project_id: str,
    user_id: str,
    labeling_task_id: str,
    name: str,
    source_code: str,
    description: str,
    type: str,
) -> InformationSource:
    labeling_task_item: LabelingTask = labeling_task.get(project_id, labeling_task_id)
    return_type: str = resolve_source_return_type(labeling_task_item)
    source: InformationSource = information_source.create(
        project_id=project_id,
        name=name,
        labeling_task_id=labeling_task_id,
        source_code=source_code,
        description=description,
        type=type,
        return_type=return_type,
        created_by=user_id,
        with_commit=True,
    )
    return source


def update_information_source(
    project_id: str,
    source_id: str,
    labeling_task_id: str,
    code: str,
    description: str,
    name: str,
) -> None:
    labeling_task_item: LabelingTask = labeling_task.get(project_id, labeling_task_id)
    return_type: str = resolve_source_return_type(labeling_task_item)
    information_source.update(
        project_id,
        source_id,
        labeling_task_id=labeling_task_id,
        return_type=return_type,
        source_code=code,
        description=description,
        name=name,
        with_commit=True,
    )


def delete_information_source(project_id: str, source_id: str) -> None:
    information_source.delete(project_id, source_id, with_commit=True)


def toggle_information_source(project_id: str, source_id: str) -> None:
    information_source.toggle(project_id, source_id, with_commit=True)


def set_all_information_source_selected(project_id: str, value: bool) -> None:
    information_source.update_is_selected_for_project(
        project_id, value, with_commit=True
    )
