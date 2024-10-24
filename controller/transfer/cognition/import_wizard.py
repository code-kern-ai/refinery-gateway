from contextvars import Token
from typing import List, Optional, Dict, Any
import json
import time
import requests
from uuid import uuid4

from submodules.model import enums
from submodules.model.business_objects import (
    general,
    attribute as attribute_db_bo,
    tokenization as tokenization_db_bo,
    project as project_db_bo,
    notification as notification_db_bo,
    record as record_db_bo,
)
from submodules.model.cognition_objects import project as cognition_project

from util import notification

from controller.upload_task import manager as upload_task_manager
from controller.labeling_task import manager as labeling_task_manager
from controller.labeling_task_label import manager as label_manager
from controller.information_source import manager as information_source_manager
from controller.attribute import manager as attribute_manager
from controller.task_master import manager as task_master_manager
from controller.embedding import manager as embedding_manager

from .bricks_loader import get_bricks_code_from_group, get_bricks_code_from_endpoint
from .constants import (
    CognitionProjects,
    DEFAULT_MODEL,
    MODEL_DOC2QUERY,
    FREE_API_REQUEST_URL,
)
from .util import send_log_message
import traceback


class TokenRef:
    def __init__(self):
        self._token = general.get_ctx_token()

    def request_new(self):
        self._token = general.remove_and_refresh_session(self._token, True)

    def cleanup(self):
        general.remove_and_refresh_session(self._token, False)


def prepare_and_finalize_setup(cognition_project_id: str, task_id: str) -> None:
    token_ref = TokenRef()
    try:
        __finalize_setup(token_ref, cognition_project_id, task_id)
    except Exception as e:
        print(f"Error during wizard setup: {str(e)}", flush=True)
        print(traceback.format_exc())
    finally:
        token_ref.cleanup()


def __finalize_setup(
    token_ref: TokenRef, cognition_project_id: str, task_id: str
) -> None:
    cognition_project_item = cognition_project.get(cognition_project_id)
    cognition_project_item.state = enums.CognitionProjectState.WIZARD_RUNNING.value
    general.commit()
    # unbind to prevent session issues
    organization_id = str(cognition_project_item.organization_id)
    reference_project_id = str(cognition_project_item.refinery_references_project_id)
    question_project_id = str(cognition_project_item.refinery_question_project_id)
    relevance_project_id = str(cognition_project_item.refinery_relevance_project_id)

    project_language = str(project_db_bo.get(reference_project_id).tokenizer_blank)

    task = upload_task_manager.get_upload_task(
        task_id=task_id,
        project_id=reference_project_id,
    )
    if not task:
        raise ValueError("Task not found")
    file_additional_info = json.loads(task.file_additional_info)

    user_id = str(task.user_id)

    send_log_message(
        question_project_id,
        "Generating questions based on references",
    )
    # first add actual records to question & relevance
    if __add_records_to_question_and_relevance(
        reference_project_id,
        question_project_id,
        relevance_project_id,
        user_id,
        project_language,
        32,
    ):
        send_log_message(
            question_project_id,
            "Generating questions based on references - finished",
        )
    else:
        send_log_message(
            question_project_id,
            "Couldn't generate enough question data - stopping wizard",
            True,
        )
        return

    # then add additional tasks to queue

    task_list = []
    __finalize_setup_for(
        CognitionProjects.REFERENCE,
        reference_project_id,
        organization_id,
        user_id,
        project_language,
        file_additional_info,
        task_list,
        token_ref,
    )
    notification.send_organization_update(
        cognition_project_id,
        "cognition_wizard:prep:REFERENCE:COMPLETE",
        organization_id=organization_id,
    )

    __finalize_setup_for(
        CognitionProjects.QUESTION,
        question_project_id,
        organization_id,
        user_id,
        project_language,
        file_additional_info,
        task_list,
        token_ref,
    )

    # sample data from references & send to doc to query

    notification.send_organization_update(
        cognition_project_id,
        "cognition_wizard:prep:QUESTION:COMPLETE",
        organization_id=organization_id,
    )

    ## additional question task creation
    qdrant_filter = file_additional_info.get("qdrant_filter", [])

    for item in qdrant_filter:
        labels = []
        if item["type"] == "ATTRIBUTE":
            labels = attribute_db_bo.get_unique_values(
                reference_project_id, item["name"]
            )
        __create_task_and_labels_for(question_project_id, item["name"], labels)

    __finalize_setup_for(
        CognitionProjects.RELEVANCE,
        relevance_project_id,
        organization_id,
        user_id,
        project_language,
        file_additional_info,
        task_list,
        token_ref,
    )
    notification.send_organization_update(
        cognition_project_id,
        "cognition_wizard:prep:RELEVANCE:COMPLETE",
        organization_id=organization_id,
    )
    task_list.append(
        {
            "organization_id": organization_id,
            "project_id": reference_project_id,
            "task_type": enums.TaskType.TASK_QUEUE_ACTION.value,
            "action": {
                "action_type": enums.TaskQueueAction.FINISH_COGNITION_SETUP.value,
                "cognition_project_id": cognition_project_id,
            },
        }
    )

    # wait for initial tokenization to finish
    c = 0
    while True:
        time.sleep(1)
        c += 1
        if c > 120:
            token_ref.request_new()
            c = 0
        if tokenization_db_bo.is_doc_bin_creation_running_or_queued(
            reference_project_id
        ):
            continue
        if tokenization_db_bo.is_doc_bin_creation_running_or_queued(
            question_project_id
        ):
            continue
        if tokenization_db_bo.is_doc_bin_creation_running_or_queued(
            relevance_project_id
        ):
            continue
        break

    queue_response = task_master_manager.queue_task(
        organization_id,
        user_id,
        enums.TaskType.TASK_QUEUE,
        {"project_id": cognition_project_id, "task_list": task_list},
    )
    if queue_response.ok:
        queue_info = queue_response.json()
        task_id = queue_info["task_id"]
        position = queue_info.get("position")

        notification.send_organization_update(
            cognition_project_id,
            f"cognition_wizard:task_queue:{task_id}:{len(task_list)}",
            organization_id=organization_id,
        )
        if position:
            notification.send_organization_update(
                cognition_project_id,
                f"task_queue:{str(task_id)}:QUEUE_POSITION:{position}",
                organization_id=organization_id,
            )


# function called from queue as last entry
def finish_cognition_setup(
    cognition_project_id: str,
) -> None:
    ctx_token = general.get_ctx_token()
    cognition_project_item = cognition_project.get(cognition_project_id)
    if not cognition_project_item:
        general.remove_and_refresh_session(ctx_token, False)
        return
    user_id = str(cognition_project_item.created_by)
    notification_db_bo.set_notifications_to_not_initial(
        str(cognition_project_item.refinery_references_project_id), user_id
    )
    notification_db_bo.set_notifications_to_not_initial(
        str(cognition_project_item.refinery_question_project_id), user_id
    )
    notification_db_bo.set_notifications_to_not_initial(
        str(cognition_project_item.refinery_relevance_project_id), user_id
    )

    cognition_project_item.state = enums.CognitionProjectState.DEVELOPMENT.value
    organization_id = str(cognition_project_item.organization_id)
    general.commit()
    general.remove_and_refresh_session(ctx_token, False)
    notification.send_organization_update(
        cognition_project_id,
        "cognition_prep:state:DONE",
        organization_id=organization_id,
    )


def __add_websocket_message_queue_item(
    sender_project_id: str,
    msg: str,
    task_list: List[Dict[str, str]],
    organization_id: Optional[str] = None,  # needs to be set for cognition project ids
) -> None:
    action = {
        "action_type": enums.TaskQueueAction.SEND_WEBSOCKET.value,
        "project_id": sender_project_id,
        "message": msg,
    }
    if organization_id:
        action["organization_id"] = organization_id
    task_list.append(
        {
            "organization_id": organization_id,
            "task_type": enums.TaskType.TASK_QUEUE_ACTION.value,
            "action": action,
        }
    )


def __add_weakly_supervise_all_valid(
    project_id: str,
    org_id: str,
    task_list: List[Dict[str, str]],
) -> None:
    task_list.append(
        {
            "organization_id": org_id,
            "task_type": enums.TaskType.TASK_QUEUE_ACTION.value,
            "action": {
                "action_type": enums.TaskQueueAction.RUN_WEAK_SUPERVISION.value,
                "project_id": project_id,
            },
        }
    )


# task_list is appended with post processing steps for the task queue
def __finalize_setup_for(
    project_type: CognitionProjects,
    project_id: str,
    org_id: str,
    user_id: str,
    project_language: str,
    file_additional_info: Dict[str, Any],
    task_list: List[Dict[str, str]],
    token_ref: TokenRef,
) -> Token:
    target_data = {"TARGET_LANGUAGE": project_language}

    # attributes
    attributes = project_type.get_attributes()
    target_data["target_type"] = "ac"
    if attributes:
        for attribute in attributes:
            if not attribute:
                # placeholder item
                continue
            run_code = attribute.get("run_code", True)
            bricks = attribute.get("bricks")
            if bricks:
                __load_ac_from_bricks_group(
                    project_id,
                    org_id,
                    bricks["group"],
                    bricks.get("type", "generator"),
                    bricks.get("type_lookup", {}),
                    target_data,
                    task_list,
                    append_to_task_list=run_code,
                )
            else:
                code = attribute.get("code")
                if not code:
                    code_build = attribute.get("code_build")
                    if not code_build:
                        raise ValueError("No code or code_build given")

                    target_data["ATTRIBUTE"] = code_build.get(
                        "target_attribute", "reference"
                    )
                    code = get_bricks_code_from_endpoint(
                        code_build["endpoint"], target_data
                    )
                __create_attribute_with(
                    project_id,
                    org_id,
                    code,
                    attribute["name"],
                    attribute["type"],
                    task_list,
                    run_code,
                )

    # tasks + functions
    labeling_tasks = project_type.get_labeling_tasks()
    task_lookup = {}  # name -> id
    target_data["target_type"] = "lf"
    if labeling_tasks:
        for task in labeling_tasks:
            task_type = task.get("task_type")
            task_attribute = task.get("target_attribute")
            if (
                task_type == enums.LabelingTaskType.INFORMATION_EXTRACTION.value
                and not task_attribute
            ):
                send_log_message(
                    project_id,
                    "Can't create extraction task without target attribute",
                    True,
                )
                continue
            if task_attribute:
                task_attribute = str(
                    attribute_db_bo.get_by_name(project_id, task_attribute).id
                )
            labeling_task_id = __create_task_and_labels_for(
                project_id,
                task["name"],
                task["labels"],
                task_type,
                target_attribute_id=task_attribute,
            )
            task_lookup[task["name"]] = labeling_task_id
            bricks = task.get("bricks")
            if bricks:
                target_attribute = bricks.get("target_attribute", "reference")
                target_data["ATTRIBUTE"] = target_attribute
                __load_lf_from_bricks_group(
                    project_id,
                    labeling_task_id,
                    user_id,
                    org_id,
                    bricks["group"],
                    bricks.get("type", "classifier"),
                    target_data,
                    task_list,
                    name_prefix=bricks.get("function_prefix"),
                )

    # embeddings
    selected_filter_attributes = [
        c["name"]
        for c in file_additional_info.get("qdrant_filter", [])
        if c["type"] == "ATTRIBUTE"
    ]

    embeddings = project_type.get_embeddings()
    target_data["target_type"] = "al"
    if embeddings:
        for embedding in embeddings:
            filter_columns = embedding.get("filter")
            if filter_columns == "FROM_WIZARD":
                filter_columns = selected_filter_attributes
            else:
                filter_columns = []
            embedding_name = __add_embedding(
                project_id,
                org_id,
                embedding.get("target", {}),
                project_language,
                filter_columns,
                embedding.get("outlier_slice", False),
                task_list,
            )
            bricks = embedding.get("bricks")
            if bricks:
                target_data["EMBEDDING"] = embedding_name
                labeling_task_id = task_lookup.get(bricks.get("target_task_name"))
                if not labeling_task_id:
                    send_log_message(
                        project_id,
                        "Can't create active learner without task name",
                        True,
                    )
                    continue
                __load_active_learner_from_bricks_group(
                    project_id,
                    labeling_task_id,
                    user_id,
                    bricks["group"],
                    bricks.get("type", "classifier"),
                    target_data,
                    name_prefix=bricks.get("function_prefix"),
                )
    __add_weakly_supervise_all_valid(project_id, org_id, task_list)
    token_ref.request_new()


def __create_task_and_labels_for(
    project_id: str,
    task_name: str,
    labels: List[str],
    task_type: Optional[str] = None,
    target_attribute_id: Optional[str] = None,
) -> str:
    if task_type is None:
        task_type = enums.LabelingTaskType.CLASSIFICATION.value

    task_item = labeling_task_manager.get_labeling_task_by_name(project_id, task_name)
    if not task_item:
        task_item = labeling_task_manager.create_labeling_task(
            project_id, task_name, task_type, target_attribute_id
        )
    else:
        existing = set([label.name for label in task_item.labels])
        labels = [label for label in labels if label not in existing]

    label_manager.create_labels(project_id, str(task_item.id), labels)
    return str(task_item.id)


def __load_lf_from_bricks_group(
    target_project_id: str,
    target_task_id: str,
    user_id: str,
    org_id: str,
    group_key: str,
    bricks_type: str,
    target_data: Dict[str, str],
    task_list: List[Dict[str, str]],
    language_key: Optional[str] = None,
    name_prefix: Optional[str] = None,
    append_to_task_list: bool = True,
) -> None:
    bricks_in_group = get_bricks_code_from_group(
        group_key,
        bricks_type,
        language_key,
        target_data,
        name_prefix,
        project_id=target_project_id,
    )
    for name in bricks_in_group:
        item = information_source_manager.create_information_source(
            target_project_id,
            user_id,
            target_task_id,
            name,
            bricks_in_group[name]["code"],
            "",
            enums.InformationSourceType.LABELING_FUNCTION.value,
        )
        if append_to_task_list:
            task_list.append(
                {
                    "organization_id": org_id,
                    "project_id": target_project_id,
                    "task_type": enums.TaskType.INFORMATION_SOURCE.value,
                    "information_source_id": str(item.id),
                    "source_type": enums.InformationSourceType.LABELING_FUNCTION.value,
                }
            )


def __load_active_learner_from_bricks_group(
    target_project_id: str,
    target_task_id: str,
    user_id: str,
    group_key: str,
    bricks_type: str,
    target_data: Dict[str, str],
    language_key: Optional[str] = None,
    name_prefix: Optional[str] = None,
) -> None:
    bricks_in_group = get_bricks_code_from_group(
        group_key,
        bricks_type,
        language_key,
        target_data,
        name_prefix,
        project_id=target_project_id,
    )
    for name in bricks_in_group:
        information_source_manager.create_information_source(
            target_project_id,
            user_id,
            target_task_id,
            name.replace("_", " ")
            .title()
            .replace(" ", ""),  # to pascal case (e.g. random_forest -> RandomForest)
            bricks_in_group[name]["code"],
            "",
            enums.InformationSourceType.ACTIVE_LEARNING.value,
        )


def __load_ac_from_bricks_group(
    target_project_id: str,
    org_id: str,
    group_key: str,
    bricks_type: str,
    data_type_lookup: Dict[str, str],
    target_data: Dict[str, str],
    task_list: List[Dict[str, str]],
    language_key: Optional[str] = None,
    name_prefix: Optional[str] = None,
    append_to_task_list: bool = True,
) -> None:
    bricks_in_group = get_bricks_code_from_group(
        group_key,
        bricks_type,
        language_key,
        target_data,
        name_prefix,
        project_id=target_project_id,
    )
    for name in bricks_in_group:
        code = bricks_in_group[name]["code"]
        data_type = data_type_lookup.get(
            bricks_in_group[name]["endpoint"], enums.DataTypes.TEXT.value
        )
        __create_attribute_with(
            target_project_id,
            org_id,
            code,
            name,
            data_type,
            task_list,
            append_to_task_list=append_to_task_list,
        )


def __add_embedding(
    target_project_id: str,
    org_id: str,
    target_info: Dict[str, str],
    project_language: str,
    filter_columns: List[str],
    create_outlier_slice: bool,
    task_list: List[Dict[str, str]],
) -> str:
    target_attribute = target_info.get("attribute", "reference")
    target_platform = target_info.get("platform", "huggingface")
    target_model = None
    if target_platform != enums.EmbeddingPlatform.COHERE.value:
        target_model = target_info.get("model", {})
        if isinstance(target_model, dict):
            target_model = target_model.get(
                project_language, DEFAULT_MODEL[target_platform]
            )
    target_embedding_type = target_info.get("embedding_type", "ON_ATTRIBUTE")
    target_api_token = target_info.get("api_token")
    attribute_item = attribute_db_bo.get_by_name(target_project_id, target_attribute)
    if not attribute_item:
        return
    attribute_id = str(attribute_item.id)
    embedding_name = embedding_manager.get_embedding_name(
        target_project_id,
        attribute_id,
        target_platform,
        target_embedding_type,
        target_model,
        target_api_token,
    )
    task_list.append(
        {
            "organization_id": org_id,
            "project_id": target_project_id,
            "task_type": enums.TaskType.EMBEDDING.value,
            "embedding_type": target_embedding_type,
            "attribute_id": attribute_id,
            "embedding_name": embedding_name,
            "platform": target_platform,
            "model": target_model,
            "api_token": target_api_token,
            "terms_text": embedding_manager.get_current_terms_text(target_platform),
            "terms_accepted": target_api_token is not None,
            "filter_attributes": filter_columns,
            "additional_data": None,
        }
    )
    if create_outlier_slice:
        task_list.append(
            {
                "organization_id": org_id,
                "project_id": target_project_id,
                "task_type": enums.TaskType.TASK_QUEUE_ACTION.value,
                "action": {
                    "action_type": enums.TaskQueueAction.CREATE_OUTLIER_SLICE.value,
                    "embedding_name": embedding_name,
                    "project_id": target_project_id,
                },
            }
        )
    return embedding_name


def __create_attribute_with(
    project_id: str,
    org_id: str,
    code: str,
    name: str,
    attribute_type: str,
    task_list: List[Dict[str, str]],
    append_to_task_list: bool = True,
) -> str:
    attribute_item = attribute_manager.create_user_attribute(
        project_id, name, attribute_type
    )
    attribute_item.source_code = code
    general.commit()
    attribute_id = str(attribute_item.id)
    if append_to_task_list:
        task_list.append(
            {
                "organization_id": org_id,
                "project_id": project_id,
                "task_type": enums.TaskType.ATTRIBUTE_CALCULATION.value,
                "attribute_id": attribute_id,
            }
        )
    return attribute_id


def __add_records_to_question_and_relevance(
    reference_project_id: str,
    question_project_id: str,
    relevance_project_id: str,
    user_id: str,
    language: str,
    amount: int,
) -> bool:
    sample_facts = record_db_bo.get_sample_data_of(
        reference_project_id,
        "reference",
        amount,
        "LENGTH(data->>'reference') BETWEEN 5 AND 1024",
    )

    if len(sample_facts) < amount:
        send_log_message(
            question_project_id,
            "Not enough sample data - we need at least 32 references between 5 and 1024 characters",
            True,
        )
        return False

    questions = __call_doc_2_query_free(language, sample_facts)

    if len(questions) != amount:
        send_log_message(
            question_project_id,
            "Not enough query data - this shouldn't happen - contact support",
            True,
        )
        return False

    max_running_id_qu = record_db_bo.get_max_running_id(question_project_id) + 1
    max_running_id_re = record_db_bo.get_max_running_id(relevance_project_id) + 1
    final_json_to_add_questions = []
    final_json_to_add_relevance = []
    for idx, (reference, question) in enumerate(zip(sample_facts, questions)):
        final_question = question
        if "?" not in final_question:
            final_question += "?"
        final_question = final_question[0].title() + final_question[1:]
        message_id = "mr-" + str(idx)
        final_json_to_add_questions.append(
            {
                "running_id": max_running_id_qu + idx,
                "message_id": message_id,
                "question": final_question,
                "question_prev_3": None,
                "answer_prev_3": None,
                "question_prev_2": None,
                "answer_prev_2": None,
                "question_prev_1": None,
                "answer_prev_1": None,
                "conversation_id": None,
            }
        )
        max_running_id_re += 1
        final_json_to_add_relevance.append(
            {
                "running_id": max_running_id_re + idx,
                "question": final_question,
                "message_id": message_id,
                "reference": reference,
                "__Fact is relevant": "Yes",
            }
        ),
    __post_to_refinery_project(
        question_project_id, user_id, final_json_to_add_questions
    )
    __post_to_refinery_project(
        relevance_project_id, user_id, final_json_to_add_relevance
    )
    return True


def __post_to_refinery_project(
    project_id: str, user_id: str, records: List[Dict[str, str]]
) -> None:
    requests.post(
        f"http://refinery-gateway:80/project/{project_id}/import_json",
        json={
            "user_id": user_id,
            "records": records,
            "request_uuid": str(uuid4()),
            "is_last": True,  # or False
        },
    )


def __call_doc_2_query_free(language: str, texts_to_query: List[str]) -> List[str]:
    if language not in MODEL_DOC2QUERY:
        raise ValueError("Language not yet supported")

    response = requests.post(
        FREE_API_REQUEST_URL,
        json={"model_name": MODEL_DOC2QUERY.get(language), "text": texts_to_query},
    )
    response.raise_for_status()
    return [r["generated_text"] for r in response.json()]


def dummy():
    pass
