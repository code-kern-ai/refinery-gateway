from typing import List, Any, Optional, Tuple, Dict
import os
import requests
from submodules.model.business_objects import (
    evaluation_group as evaluation_group_db_bo,
    evaluation_set as evaluation_set_db_bo,
    evaluation_run as evaluation_run_db_bo,
    attribute as attribute_db_bo,
    record as record_db_bo,
)
from service.search.search import resolve_extended_search
from submodules.model.util import sql_alchemy_to_dict, to_frontend_obj_raw

NEURAL_SEARCH = os.getenv("NEURAL_SEARCH")
EMBEDDING_SERVICE = os.getenv("EMBEDDING_SERVICE")

FILTER = None
THRESHOLD = None


class EVALUATION_RUN_STATE:
    INITIATED = "INITIATED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


def get_search_result_for_text(
    project_id: str,
    embedding_id: str,
    question: str,
    limit: int,
    filter=None,
    threshold=None,
):
    question_tensor = __get_tensors_for_texts(project_id, embedding_id, [question])
    if question_tensor and question_tensor[0]:
        records = __get_most_similar_records(
            project_id, embedding_id, question_tensor[0], limit, filter, threshold
        )
        # make more efficient, own function
        unfolded_records = []
        for record in records:
            record_obj = record_db_bo.get(project_id, record["id"])
            record_dict = sql_alchemy_to_dict(record_obj)
            unfolded_records.append(
                {
                    "data": record_dict["data"],
                    "id": record["id"],
                    "score": record["score"],
                }
            )
        return unfolded_records
    else:
        return []


def create_evaluation_set(
    project_id: str, question: str, record_ids: List[str], created_by: str
):
    evaluation_set_db_bo.create(project_id, question, created_by, record_ids, True)


def delete_evaluation_sets(project_id: str, set_ids: str):
    evaluation_set_db_bo.delete_all(project_id, set_ids, True)


def get_evaluation_set_by_id(project_id: str, set_id: str):
    return evaluation_set_db_bo.get(project_id, set_id)


def get_evaluation_sets(project_id: str):
    return evaluation_set_db_bo.get_all(project_id)


def get_evaluation_sets_by_group_id(project_id: str, evaluation_group_id: str):
    return evaluation_set_db_bo.get_by_evaluation_group_id(
        project_id, evaluation_group_id
    )


def create_evaluation_group(
    project_id: str, name: str, evaluation_set_ids: List[str], created_by: str
):
    evaluation_group_db_bo.create(
        project_id, name, created_by, evaluation_set_ids, True
    )


def delete_evaluation_groups(project_id: str, group_ids: str):
    evaluation_group_db_bo.delete_all(project_id, group_ids, True)


def get_evaluation_group_by_id(project_id: str, group_id: str):
    return evaluation_group_db_bo.get(project_id, group_id)


def get_evaluation_groups(project_id: str):
    return evaluation_group_db_bo.get_all(project_id)


def delete_evaluation_runs(project_id: str, run_ids: str):
    return evaluation_run_db_bo.delete_all(project_id, run_ids, True)


def get_evaluation_runs(project_id: str):
    evaluation_runs_objects = evaluation_run_db_bo.get_all(project_id)
    evaluation_runs = []
    for evaluation_run in evaluation_runs_objects:
        results = to_frontend_obj_raw(evaluation_run.results)
        evaluation_runs.append(
            {**sql_alchemy_to_dict(evaluation_run, True), "results": results}
        )
    return evaluation_runs


def get_evaluation_run_by_id(project_id: str, run_id: str):
    evaluation_run = evaluation_run_db_bo.get(project_id, run_id)
    evaluation_run_object = sql_alchemy_to_dict(evaluation_run, False)
    return evaluation_run_object


def init_evaluation_run(
    project_id: str, embedding_id: str, evaluation_group_id: str, created_by: str
):

    evaluation_run = evaluation_run_db_bo.create(
        project_id,
        evaluation_group_id,
        created_by,
        embedding_id,
        EVALUATION_RUN_STATE.INITIATED,
    )
    state = EVALUATION_RUN_STATE.RUNNING
    evaluation_results = []
    try:
        evaluation_sets = evaluation_set_db_bo.get_by_evaluation_group_id(
            project_id, evaluation_group_id
        )
        questions_tensors = __get_tensors_for_texts(
            project_id,
            embedding_id,
            [evaluation_set.question for evaluation_set in evaluation_sets],
        )
        search_results = [
            __get_most_similar_records(project_id, embedding_id, questions_tensor, 10)
            for questions_tensor in questions_tensors
        ]

        for evaluation_set, search_result in zip(evaluation_sets, search_results):

            expected_record_ids = [str(rid) for rid in evaluation_set.record_ids]
            received_record_ids = [str(record["id"]) for record in search_result]

            true_positives = []
            false_positives = []
            false_negatives = []
            for record_id in expected_record_ids:
                if record_id in received_record_ids:
                    true_positives.append(record_id)
                else:
                    false_negatives.append(record_id)

            for record_id in received_record_ids:
                if record_id not in expected_record_ids:
                    false_positives.append(record_id)

            result = {
                "evaluation_set_id": str(evaluation_set.id),
                "true_positives": to_frontend_obj_raw(
                    sql_alchemy_to_dict(
                        record_db_bo.get_by_record_ids(project_id, true_positives)
                    )
                ),
                "false_positives": to_frontend_obj_raw(
                    sql_alchemy_to_dict(
                        record_db_bo.get_by_record_ids(project_id, false_positives)
                    )
                ),
                "false_negatives": to_frontend_obj_raw(
                    sql_alchemy_to_dict(
                        record_db_bo.get_by_record_ids(project_id, false_negatives)
                    )
                ),
            }
            evaluation_results.append(result)
        state = EVALUATION_RUN_STATE.SUCCESS
    except Exception:
        state = EVALUATION_RUN_STATE.FAILED
    evaluation_run_db_bo.update(
        project_id, evaluation_run.id, state, evaluation_results, None, True
    )
    return evaluation_run


def __get_tensors_for_texts(
    refinery_project_id: str, embedding_id: str, texts: List[str]
) -> Tuple[bool, Optional[List[Any]]]:

    url = f"{EMBEDDING_SERVICE}/calc-tensor-by-pkl/{refinery_project_id}/{embedding_id}"

    response = requests.post(
        url,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
        },
        json={"texts": texts},
    )
    if response.ok:
        return response.json()["tensor"]
    else:
        return None


def __get_most_similar_records(
    project_id: str,
    embedding_id: str,
    embedding_tensor: List[float],
    limit: int,
    similarity_filter_option: Optional[List[Dict[str, Any]]] = None,
    threshold: Optional[float] = None,
):
    url = f"{NEURAL_SEARCH}/most_similar_by_embedding?include_scores=true"

    response = requests.post(
        url,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
        },
        json={
            "project_id": project_id,
            "embedding_id": embedding_id,
            "embedding_tensor": embedding_tensor,
            "limit": limit,
            "att_filter": similarity_filter_option,
            "threshold": threshold,
        },
    )
    print("response.ok", response.ok, flush=True)
    if response.ok:
        return response.json()
    else:
        return None


def get_records_by_content(
    project_id: str, user_id: str, content: str, limit: int, offset: int
):

    filter_data = __build_contains_filter(project_id, content)
    record_list = resolve_extended_search(
        project_id, user_id, filter_data, limit, offset
    ).record_list
    record_list = to_frontend_obj_raw(
        sql_alchemy_to_dict(record_list, column_blacklist=["rla_data"])
    )
    return record_list


def __build_contains_filter(project_id: str, content: str):
    attributes = attribute_db_bo.get_all(project_id)

    filter_each_attribute = [
        {
            "RELATION": "OR",
            "NEGATION": False,
            "TARGET_TABLE": "RECORD",
            "TARGET_COLUMN": "DATA",
            "OPERATOR": "CONTAINS",
            "VALUES": [f"{attribute.name}", f"{content}"],
        }
        for attribute in attributes
    ]

    if len(filter_each_attribute) > 0:
        filter_each_attribute[0]["RELATION"] = "NONE"

    final_filter = [
        {
            "RELATION": "NONE",
            "NEGATION": False,
            "TARGET_TABLE": "RECORD",
            "TARGET_COLUMN": "CATEGORY",
            "OPERATOR": "EQUAL",
            "VALUES": ["SCALE"],
        },
        {"RELATION": "AND", "NEGATION": False, "FILTER": filter_each_attribute},
    ]

    return final_filter
