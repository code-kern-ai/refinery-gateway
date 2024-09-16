import json
import os
from typing import List, Optional
from controller.information_source.util import resolve_source_return_type
from submodules.model import InformationSource, LabelingTask, enums
from submodules.model.business_objects import (
    labeling_task,
    information_source,
    payload,
)
from controller.misc import config_service
from controller.labeling_access_link import manager as link_manager
from controller.record_label_association import manager as rla_manager
from util import daemon


def get_information_source(project_id: str, source_id: str) -> InformationSource:
    return information_source.get(project_id, source_id)


def get_information_source_by_name(project_id: str, name: str) -> InformationSource:
    return information_source.get_by_name(project_id, name)


def get_all_information_sources(project_id: str) -> List[InformationSource]:
    return information_source.get_all(project_id)


def get_overview_data(project_id: str, is_model_callback: bool = False) -> str:
    return information_source.get_overview_data(project_id, is_model_callback)


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
    item = information_source.get(project_id, source_id)
    new_payload_needed = (
        str(item.source_code) != code or str(item.labeling_task_id) != labeling_task_id
    )
    item = information_source.update(
        project_id,
        source_id,
        labeling_task_id=labeling_task_id,
        return_type=return_type,
        source_code=code,
        description=description,
        name=name,
        with_commit=True,
    )

    link_manager.set_changed_for(project_id, enums.LinkTypes.HEURISTIC, source_id)


def delete_information_source(project_id: str, source_id: str) -> None:
    information_source_item = information_source.get(project_id, source_id)
    if not information_source_item:
        print(f"Information source {source_id} not found. Could not delete it.")
        return

    if (
        information_source_item.type
        == enums.InformationSourceType.ACTIVE_LEARNING.value
        and config_service.get_config_value("is_managed")
    ):
        daemon.run(__delete_active_learner_from_inference_dir, project_id, source_id)

    information_source.delete(project_id, source_id, with_commit=True)


def __delete_active_learner_from_inference_dir(project_id: str, source_id: str) -> None:
    pickle_path = os.path.join(
        "/inference", project_id, f"active-learner-{source_id}.pkl"
    )
    if os.path.exists(pickle_path):
        os.remove(pickle_path)


def delete_information_source_payload(
    project_id: str, information_source_id: str, payload_id: str
) -> None:
    payload.remove(project_id, information_source_id, payload_id, with_commit=True)


def toggle_information_source(project_id: str, source_id: str) -> None:
    information_source.toggle(project_id, source_id, with_commit=True)


def set_all_information_source_selected(project_id: str, value: bool) -> None:
    information_source.update_is_selected_for_project(
        project_id, value, with_commit=True
    )


def set_all_model_callbacks_selected(project_id: str, value: bool) -> None:
    information_source.update_is_selected_for_project(
        project_id, value, with_commit=True, is_model_callback=True
    )
