import json
import os
import shutil
import time
import threading
from typing import Any, Dict, List, Optional
from controller.embedding.manager import recreate_embeddings
from graphql import GraphQLError

from controller.transfer import project_transfer_manager as handler
from controller.labeling_access_link import manager as link_manager
from submodules.model import Project, enums
from submodules.model.business_objects import (
    labeling_task,
    organization,
    project,
    record_label_association,
    data_slice,
    embedding,
    information_source,
    general,
)
from graphql_api.types import HuddleData, ProjectSize, GatesIntegrationData
from util import daemon, notification
from controller.task_queue import manager as task_queue_manager
from submodules.model.enums import TaskType, RecordTokenizationScope
from submodules.model.business_objects import util as db_util
from submodules.s3 import controller as s3
from service.search import search
from controller.tokenization.tokenization_service import request_save_tokenizer
from controller.payload.util import has_active_learner_running
from controller.payload import manager as payload_manager
from controller.transfer.record_transfer_manager import import_records_and_rlas
from controller.transfer.manager import check_and_add_running_id
from controller.upload_task import manager as upload_task_manager
from controller.gates import gates_service


def get_project(project_id: str) -> Project:
    return project.get(project_id)


def get_project_with_orga_id(organization_id: str, project_id: str) -> Project:
    return project.get_with_organization_id(organization_id, project_id)


def get_all_projects(organization_id: str) -> List[Project]:
    return project.get_all(organization_id)


def get_all_projects_by_user(user_id) -> List[Project]:
    return project.get_all_by_user(user_id)


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

    daemon.run(__background_cleanup, org_id, project_id)


def __background_cleanup(org_id: str, project_id: str) -> None:
    __delete_project_data_from_minio(org_id, project_id)
    __delete_project_data_from_inference_dir(project_id)
    gates_service.stop_gates_project(project_id, ignore_404=True)


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
    task_queue_manager.add_task(
        str(project_item.id),
        TaskType.TOKENIZATION,
        user_id,
        {
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
        slices = data_slice.get_all(project_id, enums.SliceTypes.STATIC_DEFAULT)
        if slices and len(slices) > 0:
            return slices[0].id
    elif huddle_type == enums.LinkTypes.HEURISTIC.value:
        return information_source.get_first_crowd_is_for_annotator(project_id, user_id)
    else:
        raise ValueError("invalid huddle type")


# WORKFLOW


def add_workflow_store_data_to_project(
    project_id: str, user_id: str, file_name: str, data: List[Dict[str, Any]]
):
    upload_task = upload_task_manager.create_upload_task(
        user_id=user_id,
        project_id=project_id,
        file_name=file_name,
        file_type=enums.RecordImportFileTypes.JSON.value,
        file_import_options="",
        upload_type=enums.UploadTypes.WORKFLOW_STORE.value,
    )
    import_records_and_rlas(
        project_id,
        user_id,
        data,
        upload_task,
        enums.RecordCategory.SCALE.value,
    )
    check_and_add_running_id(project_id, user_id)

    upload_task_manager.update_upload_task_to_finished(upload_task)


# GATES
projects_updating = set()
projects_updating_lock = threading.Lock()


def get_gates_integration_data(project_id: str) -> GatesIntegrationData:
    project_item = project.get(project_id)
    if not project_item:
        raise GraphQLError("Project not found")

    missing_tokenizer = not __tokenizer_pickle_exists(project_item.tokenizer)
    missing_embeddings = __get_missing_embedding_pickles(project_id)
    missing_information_sources = __get_missing_information_source_pickles(project_id)

    if project_id in projects_updating:
        return GatesIntegrationData(
            status=enums.GatesIntegrationStatus.UPDATING.value,
            missing_tokenizer=missing_tokenizer,
            missing_embeddings=missing_embeddings,
            missing_information_sources=missing_information_sources,
        )

    status = enums.GatesIntegrationStatus.READY.value
    if (
        missing_tokenizer
        or len(missing_embeddings) > 0
        or len(missing_information_sources) > 0
    ):
        status = enums.GatesIntegrationStatus.NOT_READY.value

    return GatesIntegrationData(
        status=status,
        missing_tokenizer=missing_tokenizer,
        missing_embeddings=missing_embeddings,
        missing_information_sources=missing_information_sources,
    )


def __tokenizer_pickle_exists(config_string: str) -> bool:
    tokenizer_path = os.path.join(
        "/inference/tokenizers", f"tokenizer-{config_string}.pkl"
    )
    return os.path.exists(tokenizer_path)


def __get_missing_embedding_pickles(project_id: str) -> List[str]:
    missing = []
    embedding_items = embedding.get_finished_embeddings(project_id)
    for embedding_item in embedding_items:
        embedding_id = str(embedding_item.id)
        emb_path = os.path.join(
            "/inference", project_id, f"embedder-{embedding_id}.pkl"
        )
        if not os.path.exists(emb_path):
            missing.append(embedding_id)
    return missing


def __get_missing_information_source_pickles(project_id: str) -> List[str]:
    missing = []
    is_items = information_source.get_all(project_id)
    for is_item in is_items:
        if is_item.type != enums.InformationSourceType.ACTIVE_LEARNING.value:
            # only active learning information sources are pickled
            continue
        is_id = str(is_item.id)
        last_payload = information_source.get_last_payload(project_id, is_id)
        if not last_payload:
            continue
        if last_payload.state == enums.PayloadState.FINISHED.value:
            al_path = os.path.join(
                "/inference", project_id, f"active-learner-{is_id}.pkl"
            )
            if not os.path.exists(al_path):
                missing.append(is_id)
    return missing


def update_project_for_gates(project_id: str, user_id: str) -> None:
    project_item = project.get(project_id)
    if not project_item:
        return

    global projects_updating
    with projects_updating_lock:
        if project_id in projects_updating:
            return
        projects_updating.add(project_id)

    notification.send_organization_update(project_id, "gates_integration:started")

    daemon.run(
        __update_project_for_gates_thread,
        project_id,
        user_id,
        project_item,
    )


def __update_project_for_gates_thread(
    project_id: str, user_id: str, project_item: Project
) -> None:
    try:
        session_token = general.get_ctx_token()

        if not __tokenizer_pickle_exists(project_item.tokenizer):
            request_save_tokenizer(project_item.tokenizer)

        session_token = __create_missing_embedding_pickles(project_id, session_token)
        session_token = __create_missing_information_source_pickles(
            project_id, user_id, session_token
        )

    except Exception as e:
        print(f"Error while updating project {project_id} for gates: {e}")
    finally:
        global projects_updating
        with projects_updating_lock:
            if project_id in projects_updating:
                projects_updating.remove(project_id)
        notification.send_organization_update(project_id, "gates_integration:finished")
        general.remove_and_refresh_session(session_token)


def __create_missing_embedding_pickles(project_id: str, session_token: Any) -> Any:
    missing_emb_pickles = __get_missing_embedding_pickles(project_id)
    recreate_embeddings(project_id, missing_emb_pickles)
    return session_token


def __create_missing_information_source_pickles(
    project_id: str,
    user_id: str,
    session_token: Any,
) -> Any:
    missing_is_ids = __get_missing_information_source_pickles(project_id)
    for is_id in missing_is_ids:
        session_token = general.remove_and_refresh_session(
            session_token, request_new=True
        )
        payload_manager.create_payload(project_id, is_id, user_id)
        time.sleep(1)
        while has_active_learner_running(project_id):
            time.sleep(1)

    return session_token


def check_in_deletion_projects() -> None:
    # this is only supposed to be called during startup of the application
    daemon.run(__check_in_deletion_projects)


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
