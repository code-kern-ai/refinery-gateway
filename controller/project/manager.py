import json
import os
import shutil
import time
from typing import Dict, List, Optional

from controller.transfer import project_transfer_manager as handler
from controller.labeling_access_link import manager as link_manager
from submodules.model import Project, enums
from submodules.model.business_objects import (
    labeling_task,
    organization,
    project,
    record,
    record_label_association,
    data_slice,
    information_source,
    general,
)
from submodules.model import daemon
from fast_api.types import HuddleData, ProjectSize
from controller.task_master import manager as task_master_manager
from submodules.model.enums import TaskType, RecordTokenizationScope
from submodules.model.business_objects import util as db_util
from submodules.s3 import controller as s3
from service.search import search
from controller.auth import kratos
from submodules.model.util import sql_alchemy_to_dict

ALL_PROJECTS_WHITELIST = {
    "id",
    "name",
    "description",
    "tokenizer",
    "status",
    "created_at",
    "created_by",
}


def get_project(project_id: str) -> Project:
    return project.get(project_id)


def get_project_with_labeling_tasks(project_id: str) -> Project:
    return project.get_with_labling_tasks(project_id)


def get_project_with_labeling_tasks_info_attributes(project_id: str) -> Project:
    return project.get_with_labling_tasks_info_attributes(project_id)


def get_project_with_orga_id(organization_id: str, project_id: str) -> Project:
    return project.get_with_organization_id(organization_id, project_id)


def get_all_projects(organization_id: str) -> List[Project]:
    return project.get_all(organization_id)


def get_all_projects_by_user(organization_id) -> List[Project]:
    projects = project.get_all_by_user_organization_id(organization_id)
    project_dicts = sql_alchemy_to_dict(
        projects, column_whitelist=ALL_PROJECTS_WHITELIST
    )

    for p in project_dicts:
        user_id = p["created_by"]
        names, mail = kratos.resolve_user_name_and_email_by_id(user_id)
        last_name = names.get("last", "")
        first_name = names.get("first", "")
        p["user"] = {
            "mail": mail,
            "first_name": first_name,
            "last_name": last_name,
        }

        if p["status"] == enums.ProjectStatus.IN_DELETION.value:
            p["num_data_scale_uploaded"] = -1
        else:
            p["num_data_scale_uploaded"] = record.get_count_scale_uploaded(p["id"])

        del p["created_by"]

    return project_dicts


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


def get_max_running_id(project_id: str) -> int:
    return project.get_max_running_id(project_id)


def is_rats_tokenization_still_running(project_id: str) -> bool:
    return project.is_rats_tokenization_still_running(project_id)


def create_project(
    organization_id: str, name: str, description: str, user_id: str
) -> Project:
    if not s3.bucket_exists(organization_id):
        s3.create_bucket(organization_id)

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

    daemon.run_without_db_token(__background_cleanup, org_id, project_id)


def __background_cleanup(org_id: str, project_id: str) -> None:
    __delete_project_data_from_minio(org_id, project_id)
    __delete_project_data_from_inference_dir(project_id)


def __delete_project_data_from_minio(org_id, project_id: str) -> None:
    objects = s3.get_bucket_objects(org_id, project_id + "/")
    for obj in objects:
        s3.delete_object(org_id, obj)


def __delete_project_data_from_inference_dir(project_id: str) -> None:
    project_dir = os.path.join("/inference", project_id)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)


def import_sample_project(
    user_id: str, organization_id: str, name: str, project_type: str
) -> Project:
    project_item = handler.import_sample_project(
        user_id, organization_id, name, project_type
    )
    task_master_manager.queue_task(
        str(organization_id),
        str(user_id),
        TaskType.TOKENIZATION,
        {
            "project_id": str(project_item.id),
            "scope": RecordTokenizationScope.PROJECT.value,
            "include_rats": True,
            "only_uploaded_attributes": False,
        },
    )
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
            ) = data_slice.get_record_ids_and_first_unlabeled_pos(
                project_id,
                user_id,
                slice_id,
                source_type,
                source_id,
                huddle.allowed_task,
            )
    huddle.huddle_id = data_id
    huddle.checked_at = db_util.get_db_now()
    return huddle


def __no_huddle_id(data_id: str) -> bool:
    return data_id == link_manager.DUMMY_LINK_ID or not data_id


def __get_crowd_label_is_data(project_id: str, is_id: str) -> Dict[str, str]:
    information_source_item = information_source.get(project_id, is_id)
    if not information_source_item:
        raise ValueError(
            "only crowd labeler information source can be used to get a slice id"
        )

    values = json.loads(information_source_item.source_code)
    values["labeling_task_id"] = information_source_item.labeling_task_id
    return values


def __get_first_data_id(project_id: str, user_id: str, huddle_type: str) -> str:
    if huddle_type == enums.LinkTypes.DATA_SLICE.value:
        slices = data_slice.get_all(project_id, enums.SliceTypes.STATIC_DEFAULT)
        if slices and len(slices) > 0:
            return slices[0].id
    else:
        raise ValueError("invalid huddle type")


def check_in_deletion_projects() -> None:
    # this is only supposed to be called during startup of the application
    daemon.run_without_db_token(__check_in_deletion_projects)


def __check_in_deletion_projects() -> None:
    # wait for startup to finish
    time.sleep(2)
    ctx_token = general.get_ctx_token()
    to_be_deleted = []
    orgs = organization.get_all()
    for org_item in orgs:
        projects = project.get_all(str(org_item.id))
        for project_item in projects:
            if project_item.status == enums.ProjectStatus.IN_DELETION.value:
                to_be_deleted.append(str(project_item.id))
    for project_id in to_be_deleted:
        delete_project(project_id)
    general.remove_and_refresh_session(ctx_token)
