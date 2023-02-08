import json
import os
import shutil
import time
import threading
from typing import Dict, List, Optional
from graphql import GraphQLError

from controller.transfer import project_transfer_manager as handler
from controller.labeling_access_link import manager as link_manager
from submodules.model import Project, enums
from submodules.model.business_objects import (
    attribute,
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
from controller.misc import config_service
from controller.tokenization.tokenization_service import request_tokenize_project
from submodules.model.business_objects import util as db_util
from submodules.s3 import controller as s3
from service.search import search
from controller.tokenization.tokenization_service import request_save_tokenizer
from controller.embedding.connector import (
    request_creating_attribute_level_embedding,
    request_creating_token_level_embedding,
    request_deleting_embedding,
)
from controller.embedding.util import has_encoder_running
from controller.payload import manager as payload_manager


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

    daemon.run(__delete_project_data_from_minio, org_id, project_id)
    if config_service.get_config_value("is_managed"):
        daemon.run(__delete_project_data_from_inference_dir, project_id)


def __delete_project_data_from_minio(org_id, project_id: str) -> None:
    objects = s3.get_bucket_objects(org_id, project_id + "/")
    for obj in objects:
        s3.delete_object(org_id, obj)


def __delete_project_data_from_inference_dir(project_id: str) -> None:
    project_dir = os.path.join("/inference", project_id)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)


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


# GATES
projects_updating = set()
projects_updating_lock = threading.Lock()


def get_gates_integration_data(project_id: str) -> GatesIntegrationData:

    project_item = project.get(project_id)
    if not project_item:
        raise GraphQLError("Project not found")

    if project_id in projects_updating:
        return GatesIntegrationData(status=enums.GatesIntegrationStatus.UPDATING.value)

    missing_tokenizer = not __tokenizer_pickle_exists(project_item.tokenizer)
    missing_embeddings = __get_missing_embedding_pickles(project_id)
    missing_information_sources = __get_missing_information_source_pickles(project_id)

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

    if not __tokenizer_pickle_exists(project_item.tokenizer):
        daemon.run(request_save_tokenizer, project_item.tokenizer)

    missing_emb_pickles = __get_missing_embedding_pickles(project_id)
    daemon.run(
        __create_missing_embedding_pickles, project_id, user_id, missing_emb_pickles
    )

    # removes the project from the set of projects that are currently updating
    # when the function returns
    daemon.run(
        __wait_and_create_information_source_pickles,
        project_id,
        user_id,
    )


def __create_missing_embedding_pickles(
    project_id: str, user_id: str, missing_embedding_ids: List[str]
):
    for embedding_id in missing_embedding_ids:
        __create_embedding_pickle(project_id, embedding_id, user_id)
        time.sleep(10)
        while has_encoder_running(project_id):
            time.sleep(10)


def __create_embedding_pickle(project_id: str, embedding_id: str, user_id: str):

    embedding_item = embedding.get(project_id, embedding_id)
    if not embedding_item:
        return

    request_deleting_embedding(project_id, embedding_id)

    attribute_id = str(embedding_item.attribute_id)
    attribute_name = attribute.get(project_id, attribute_id).name
    if embedding_item.type == enums.EmbeddingType.ON_ATTRIBUTE.value:
        prefix = f"{attribute_name}-classification-"
        config_string = embedding_item.name[len(prefix) :]
        request_creating_attribute_level_embedding(
            project_id, attribute_id, user_id, config_string
        )
    else:
        prefix = f"{attribute_name}-extraction-"
        config_string = embedding_item.name[len(prefix) :]
        request_creating_token_level_embedding(
            project_id, attribute_id, user_id, config_string
        )


def __wait_and_create_information_source_pickles(
    project_id: str,
    user_id: str,
) -> None:
    # wait to make sure db entries for embeddings are created
    time.sleep(5)
    __wait_for_tokenizer(project_id)
    __wait_for_embeddings(project_id)

    missing_is_ids = __get_missing_information_source_pickles(project_id)
    for is_id in missing_is_ids:
        payload_manager.create_payload(project_id, is_id, user_id)

    global projects_updating
    with projects_updating_lock:
        if project_id in projects_updating:
            projects_updating.remove(project_id)

    notification.send_organization_update(project_id, "gates_integration:finished")


def __wait_for_tokenizer(project_id: str) -> None:
    while not __tokenizer_pickle_exists(project.get(project_id).tokenizer):
        time.sleep(1)


def __wait_for_embeddings(project_id: str) -> None:
    session_token = general.get_ctx_token()

    embedding_items = embedding.get_project_embeddings(project_id)
    embedding_ids = [str(embedding_item.id) for embedding_item in embedding_items]
    while embedding_ids:
        time.sleep(1)
        session_token = general.remove_and_refresh_session(
            session_token, request_new=True
        )
        for emb_id in embedding_ids:
            emb_item = embedding.get(project_id, emb_id)
            if not emb_item:
                embedding_ids.remove(emb_id)
                continue
            if emb_item.state in [
                enums.EmbeddingState.FINISHED.value,
                enums.EmbeddingState.FAILED.value,
            ]:
                embedding_ids.remove(emb_id)

    general.remove_and_refresh_session(session_token)
