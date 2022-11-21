from typing import List, Dict, Any

from graphql_api.types import ExtendedSearch
from submodules.model import Record, Attribute
from submodules.model.business_objects import general, record, user_session, embedding
from service.search import search

from controller.record import neural_search_connector
from controller.embedding import manager as embedding_manager
from util import daemon


def get_record(project_id: str, record_id: str) -> Record:
    return record.get(project_id, record_id)


def get_records_by_similarity_search(
    project_id: str,
    user_id: str,
    embedding_id: str,
    record_id: str,
) -> ExtendedSearch:
    record_ids = neural_search_connector.request_most_similar_record_ids(
        project_id, embedding_id, record_id, 100
    )
    if not len(record_ids):
        record_ids = [record_id]
    filter_data = [
        {
            "RELATION": "NONE",
            "NEGATION": False,
            "TARGET_TABLE": "RECORD",
            "TARGET_COLUMN": "ID",
            "OPERATOR": "IN",
            "VALUES": record_ids,
        }
    ]
    extended_search = get_records_by_extended_search(
        project_id, user_id, filter_data, 100, 0
    )
    # sort record list in extended search in the same ordes as the record_ids returned by the neural search
    extended_search.record_list.sort(key=lambda x: record_ids.index(str(x["id"])))

    # to ensure the same order of the labeling session
    user_session.set_record_ids(
        project_id, extended_search.session_id, record_ids, with_commit=True
    )

    return extended_search


def get_records_by_composite_keys(
    project_id: str,
    records_data: List[Dict[str, Any]],
    primary_keys: List[Attribute],
    category: str,
):
    return record.get_existing_records_by_composite_key(
        project_id, records_data, primary_keys, category
    )


def get_all_records(project_id: str) -> List[Record]:
    return record.get_all(project_id)


def get_records_by_static_slice(
    user_id: str,
    project_id: str,
    slice_id: str,
    order_by: Dict[str, str],
    limit: int,
    offset: int,
) -> ExtendedSearch:
    return search.resolve_records_by_static_slice(
        user_id, project_id, slice_id, order_by, limit, offset
    )


def get_records_by_extended_search(
    project_id: str,
    user_id: str,
    filter_data: List[Dict[str, Any]],
    limit: int,
    offset: int,
) -> ExtendedSearch:
    return search.resolve_extended_search(
        project_id, user_id, filter_data, limit, offset
    )


def delete_record(project_id: str, record_id: str) -> None:
    record.delete(project_id, record_id, with_commit=True)
    daemon.run(__reupload_embeddings, project_id)


def delete_all_records(project_id: str) -> None:
    record.delete_all(project_id, with_commit=True)


def __reupload_embeddings(project_id: str) -> None:
    embeddings = embedding.get_finished_embeddings(project_id)
    for e in embeddings:
        embedding_manager.request_tensor_upload(project_id, str(e.id))
