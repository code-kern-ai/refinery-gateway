import json
from typing import List, Optional
from controller.information_source.util import resolve_source_return_type
from submodules.model import InformationSource, LabelingTask, enums
from submodules.model.business_objects import (
    general,
    labeling_task,
    information_source,
    payload,
)
from controller.labeling_access_link import manager as link_manager
from controller.record_label_association import manager as rla_manager
from controller.payload import manager as payload_manager


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


def create_crowd_information_source(
    creation_user_id: str,
    project_id: str,
    labeling_task_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> InformationSource:
    parameter = {"data_slice_id": None, "annotator_id": None, "access_link_id": None}
    parameter = json.dumps(parameter)
    if not description:
        description = "Heuristic to provide annotators with a link"
    if not name:
        name = "Crowd Heuristic"

    crowd = create_information_source(
        project_id=project_id,
        user_id=creation_user_id,
        labeling_task_id=labeling_task_id,
        name=name,
        source_code=parameter,
        description=description,
        type=enums.InformationSourceType.CROWD_LABELER.value,
    )

    return crowd


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

    if item.type == enums.InformationSourceType.CROWD_LABELER.value:
        slice_id = json.loads(item.source_code)["data_slice_id"]
        if slice_id:
            if new_payload_needed and len(item.payloads) > 0:
                delete_information_source_payload(
                    project_id, source_id, str(item.payloads[0].id)
                )
            rla_manager.update_annotator_progress(
                project_id, source_id, item.created_by
            )
    link_manager.set_changed_for(project_id, enums.LinkTypes.HEURISTIC, source_id)


def delete_information_source(project_id: str, source_id: str) -> None:
    information_source.delete(project_id, source_id, with_commit=True)


def delete_information_source_payload(
    project_id: str, information_source_id: str, payload_id: str
) -> None:
    information_source_item = information_source.get(project_id, information_source_id)
    if information_source_item.type != enums.InformationSourceType.CROWD_LABELER.value:
        raise ValueError("Information source is not a crowd labeler")
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
