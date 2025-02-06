from typing import List, Any, Optional, Tuple, Dict
import os
import requests
from controller.embedding.connector import request_tensor_for_text
from submodules.model.business_objects import (
    evaluation_group as evaluation_group_db_bo,
    evaluation_set as evaluation_set_db_bo,
    evaluation_run as evaluation_run_db_bo,
    playground_question as playground_question_db_bo,
    attribute as attribute_db_bo,
    record as record_db_bo,
)
from service.search.search import resolve_extended_search
from submodules.model.enums import EvaluationRunState
from submodules.model.util import sql_alchemy_to_dict, to_frontend_obj_raw
from concurrent.futures import ThreadPoolExecutor
from .reformulation import reformulate_question
import json

NEURAL_SEARCH = os.getenv("NEURAL_SEARCH")
EMBEDDING_SERVICE = os.getenv("EMBEDDING_SERVICE")

EVALUATION_RUN_LIMIT_DEFAULT = 100


def get_search_result_for_text(
    project_id: str,
    embedding_id: str,
    question: str,
    limit: int,
    filter=None,
    threshold=None,
):
    question_tensor = __get_tensors_for_texts(project_id, embedding_id, [question])
    if not question_tensor or not question_tensor[0]:
        return []

    records = __get_most_similar_records(
        project_id,
        embedding_id,
        question_tensor[0],
        limit,
        filter,
        threshold,
        question,
    )

    record_ids = [record["id"] for record in records]
    record_obj_map = record_db_bo.get_full_record_data_for_id_group(
        project_id, record_ids
    )

    return [
        {
            "data": record_obj_map.get(record["id"]),
            "id": record["id"],
            "score": record["score"],
        }
        for record in records
    ]


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
    return [__pack_evaluation_run(run) for run in evaluation_runs_objects]


def get_evaluation_run_by_id(project_id: str, run_id: str):
    evaluation_run_object = evaluation_run_db_bo.get(project_id, run_id)
    return __pack_evaluation_run(evaluation_run_object)


def init_evaluation_run(
    project_id: str,
    embedding_id: str,
    evaluation_group_id: str,
    created_by: str,
    threshold: float,
):
    evaluation_run = evaluation_run_db_bo.create(
        project_id,
        evaluation_group_id,
        created_by,
        embedding_id,
        EvaluationRunState.RUNNING,
    )
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

        with ThreadPoolExecutor(max_workers=min(10, len(evaluation_sets))) as executor:
            futures = [
                executor.submit(
                    __get_most_similar_records,
                    project_id,
                    embedding_id,
                    questions_tensors[index],
                    EVALUATION_RUN_LIMIT_DEFAULT,
                    None,
                    threshold,
                )
                for index, evaluation_set in enumerate(evaluation_sets)
            ]

            search_results = [future.result() for future in futures]

        all_record_ids = set()
        for evaluation_set, search_result in zip(evaluation_sets, search_results):
            expected_record_ids = {str(rid) for rid in evaluation_set.record_ids}
            received_record_ids = {str(record["id"]) for record in search_result}
            all_record_ids.update(expected_record_ids | received_record_ids)

        all_records = record_db_bo.get_by_record_ids(project_id, list(all_record_ids))
        record_map = {
            str(record.id): sql_alchemy_to_dict(record) for record in all_records
        }

        for evaluation_set, search_result in zip(evaluation_sets, search_results):
            expected_record_ids = {str(rid) for rid in evaluation_set.record_ids}
            received_record_ids = {str(record["id"]) for record in search_result}

            true_positives = expected_record_ids & received_record_ids
            false_negatives = expected_record_ids - received_record_ids
            false_positives = received_record_ids - expected_record_ids

            result = {
                "evaluation_set_id": str(evaluation_set.id),
                "true_positives": to_frontend_obj_raw(
                    [record_map[record_id] for record_id in true_positives]
                ),
                "false_positives": to_frontend_obj_raw(
                    [record_map[record_id] for record_id in false_positives]
                ),
                "false_negatives": to_frontend_obj_raw(
                    [record_map[record_id] for record_id in false_negatives]
                ),
            }
            evaluation_results.append(result)
        state = EvaluationRunState.SUCCESS
    except Exception:
        state = EvaluationRunState.FAILED
    evaluation_run_db_bo.update(
        project_id, evaluation_run.id, state, evaluation_results, None, True
    )
    return evaluation_run


def __get_tensors_for_texts(
    refinery_project_id: str, embedding_id: str, texts: List[str]
) -> Tuple[bool, Optional[List[Any]]]:

    obj = request_tensor_for_text(refinery_project_id, embedding_id, texts)

    return obj.get("tensor", None)


def __get_most_similar_records(
    project_id: str,
    embedding_id: str,
    embedding_tensor: List[float],
    limit: int,
    similarity_filter_option: Optional[List[Dict[str, Any]]] = None,
    threshold: Optional[float] = None,
    question: Optional[str] = None,
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
            "question": question,
        },
    )
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


def __pack_evaluation_run(evaluation_run):
    return {
        **sql_alchemy_to_dict(evaluation_run, True),
        "results": to_frontend_obj_raw(evaluation_run.results),
    }


def get_question_reformulation(question: str, api_key: str) -> Optional[Dict]:
    q_reformulated = reformulate_question(question, api_key)
    try:
        reformulation_dict = json.loads(q_reformulated)
        return reformulation_dict
    except Exception:
        return None


def get_playground_questions(project_id: str):
    return playground_question_db_bo.get_all(project_id)
