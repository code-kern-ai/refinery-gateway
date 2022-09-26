import json
from typing import Dict, List, Optional

from controller.transfer import project_transfer_manager as handler
from controller.labeling_access_link import manager as link_manager
from submodules.model import Project, enums
from submodules.model.business_objects import (
    labeling_task,
    organization,
    project,
    record_label_association,
    data_slice,
)
from graphql_api.types import HuddleData, ProjectSize
from util import daemon
from controller.tokenization.tokenization_service import request_tokenize_project
from submodules.model.business_objects import data_slice as ds_manager
from submodules.model.business_objects import (
    information_source as information_source_manager,
)
from submodules.model.business_objects import util as db_util
from submodules.s3 import controller as s3
from service.search import search


def get_project(project_id: str) -> Project:
    return project.get(project_id)


def get_project_with_orga_id(organization_id: str, project_id: str) -> Project:
    return project.get_with_organization_id(organization_id, project_id)


def get_all_projects(organization_id: str) -> List[Project]:
    return project.get_all(organization_id)


def get_project_size(project_id: str) -> List[ProjectSize]:
    # might need some better logic for default true false (e.g. switch case for table names)
    disabled_default = [
        "embedding tensors",
        "record attribute token statistics",
    ]
    project_size_items = project.get_project_size(project_id)
    return [
        ProjectSize(
            order=item.order_,
            table=item.table_,
            description=item.description,
            default=False if item.table_ in disabled_default else True,
            byte_size=item.prj_size_bytes,
            byte_readable=item.prj_size_readable,
        )
        for item in project_size_items
    ]


def is_rats_tokenization_still_running(project_id: str) -> bool:
    return project.is_rats_tokenization_still_running(project_id)


def create_project(
    organization_id: str, name: str, description: str, user_id: str
) -> Project:
    project_item = project.create(
        organization_id, name, description, user_id, with_commit=True
    )
    return project_item


def update_project(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    tokenizer: Optional[str] = None,
) -> None:
    project.update(project_id, name, description, status, tokenizer, with_commit=True)


def delete_project(project_id: str) -> None:
    org_id = organization.get_id_by_project_id(project_id)
    project.delete_by_id(project_id, with_commit=True)
    daemon.run(s3.archive_bucket, org_id, project_id + "/")


def import_sample_project(user_id: str, organization_id: str, name: str) -> Project:
    project_item = handler.import_sample_project(user_id, organization_id, name)
    request_tokenize_project(str(project_item.id), str(user_id))
    record_label_association.update_is_valid_manual_label_for_project(
        str(project_item.id)
    )
    data_slice.update_slice_type_manual_for_project(
        str(project_item.id), with_commit=True
    )

    return project_item


def get_general_project_stats(
    project_id: str,
    labeling_task_id: Optional[str] = None,
    slice_id: Optional[str] = None,
) -> str:
    return project.get_general_project_stats(project_id, labeling_task_id, slice_id)


def get_label_distribution(
    project_id: str,
    labeling_task_id: Optional[str] = None,
    slice_id: Optional[str] = None,
) -> str:
    return project.get_label_distribution(project_id, labeling_task_id, slice_id)


def get_confidence_distribution(
    project_id: str,
    labeling_task_id: str,
    slice_id: Optional[str] = None,
    num_samples: Optional[int] = None,
) -> str:
    return project.get_confidence_distribution(
        project_id, labeling_task_id, slice_id, num_samples
    )


def get_confusion_matrix(
    project_id: str,
    labeling_task_id: str,
    slice_id: Optional[str] = None,
) -> str:
    for_classification = (
        labeling_task.get(project_id, labeling_task_id).task_type
        == enums.LabelingTaskType.CLASSIFICATION.value
    )
    return project.get_confusion_matrix(
        project_id, labeling_task_id, for_classification, slice_id
    )


def resolve_request_huddle_data(
    project_id: str, user_id: str, data_id: str, huddle_type: str
) -> HuddleData:
    huddle = HuddleData(huddle_type=huddle_type, start_pos=-1, can_edit=True)
    if huddle_type == enums.LinkTypes.SESSION.value:
        session = search.resolve_labeling_session(project_id, user_id, data_id)
        huddle.record_ids = session.session_record_ids
        if __no_huddle_id(data_id):
            data_id = session.id
    else:
        source_type = enums.LabelSource.MANUAL
        source_id = None
        if __no_huddle_id(data_id):
            data_id = __get_first_data_id(project_id, user_id, huddle_type)

        if huddle_type == enums.LinkTypes.DATA_SLICE.value and data_id:
            slice_id = data_id
        elif huddle_type == enums.LinkTypes.HEURISTIC.value and data_id:
            information_source_data = __get_crowd_label_is_data(project_id, data_id)
            slice_id = information_source_data["data_slice_id"]
            huddle.allowed_task = information_source_data["labeling_task_id"]
            huddle.can_edit = information_source_data["annotator_id"] == user_id
            source_type = enums.LabelSource.INFORMATION_SOURCE
            source_id = data_id
        if data_id:
            (
                huddle.record_ids,
                huddle.start_pos,
            ) = ds_manager.get_record_ids_and_first_unlabeled_pos(
                project_id, user_id, slice_id, source_type, source_id
            )
    huddle.huddle_id = data_id
    huddle.checked_at = db_util.get_db_now()
    return huddle


def __no_huddle_id(data_id: str) -> bool:
    return data_id == link_manager.DUMMY_LINK_ID or not data_id


def __get_crowd_label_is_data(project_id: str, is_id: str) -> Dict[str, str]:
    information_source_item = information_source_manager.get(project_id, is_id)
    if (
        not information_source_item
        or information_source_item.type
        != enums.InformationSourceType.CROWD_LABELER.value
    ):
        raise ValueError(
            "only crowd labeler information source can be used to get a slice id"
        )

    values = json.loads(information_source_item.source_code)
    values["labeling_task_id"] = information_source_item.labeling_task_id
    return values


def __get_first_data_id(project_id: str, user_id: str, huddle_type: str) -> str:
    if huddle_type == enums.LinkTypes.DATA_SLICE.value:
        slices = ds_manager.get_all(project_id, enums.SliceTypes.STATIC_DEFAULT)
        if slices and len(slices) > 0:
            return slices[0].id
    elif huddle_type == enums.LinkTypes.HEURISTIC.value:
        return information_source_manager.get_first_crowd_is_for_annotator(
            project_id, user_id
        )
    else:
        raise ValueError("invalid huddle type")
