from typing import List, Dict, Any, Optional
import os, copy

from graphql_api.types import ExtendedSearch
from submodules.model import Record, Attribute
from submodules.model.business_objects import (
    record,
    user_session,
    embedding,
    attribute,
    general,
    tokenization,
    task_queue,
    record_label_association,
)
from service.search import search
from submodules.model import enums

from controller.embedding import connector as embedding_connector
from controller.record import neural_search_connector
from controller.embedding import manager as embedding_manager
from controller.tokenization import tokenization_service
from util import daemon
from util.miscellaneous_functions import chunk_list
import time
import traceback


def get_record(project_id: str, record_id: str) -> Record:
    return record.get(project_id, record_id)


def get_records_by_similarity_search(
    project_id: str,
    user_id: str,
    embedding_id: str,
    record_id: str,
    att_filter: Optional[List[Dict[str, Any]]] = None,
    record_sub_key: Optional[int] = None,
) -> ExtendedSearch:
    record_ids = neural_search_connector.request_most_similar_record_ids(
        project_id, embedding_id, record_id, 100, att_filter, record_sub_key
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
    ctx_token = general.get_ctx_token()
    embeddings = embedding.get_finished_embeddings(project_id)
    for e in embeddings:
        embedding_manager.request_tensor_upload(project_id, str(e.id))
    general.remove_and_refresh_session(ctx_token)


def get_unique_values_by_attributes(project_id: str) -> Dict[str, List[str]]:
    return attribute.get_unique_values_by_attributes(project_id)


def edit_records(
    user_id: str, project_id: str, changes: Dict[str, Any]
) -> Optional[List[str]]:
    prepped = __check_and_prep_edit_records(project_id, changes)
    if "errors_found" in prepped:
        return prepped["errors_found"]

    records = prepped["records"]

    for key in changes:
        record = records[changes[key]["recordId"]]
        # needs new object to detect changes for commit
        new_data = copy.deepcopy(record.data)
        if "subKey" in changes[key]:
            new_data[changes[key]["attributeName"]][changes[key]["subKey"]] = changes[
                key
            ]["newValue"]
        else:
            new_data[changes[key]["attributeName"]] = changes[key]["newValue"]
        record.data = new_data
    general.commit()

    # remove labels
    for chunk in chunk_list(prepped["rla_delete_tuples"], 1):
        record_label_association.delete_by_record_attribute_tuples(project_id, chunk)

    general.commit()

    try:
        # tokenization currently with a complete rebuild of the docbins of touched records
        # optimization possible by only rebuilding the changed record & attribute combinations and reuploading
        tokenization.delete_record_docbins_by_id(project_id, records.keys(), True)
        tokenization.delete_token_statistics_by_id(project_id, records.keys(), True)
        tokenization_service.request_tokenize_project(project_id, user_id)
        time.sleep(1)
        # wait for tokenization to finish, the endpoint itself handles missing docbins
        while tokenization.is_doc_bin_creation_running_or_queued(project_id):
            time.sleep(0.5)

    except Exception as e:
        __revert_record_data_changes(records, prepped["record_data_backup"])
        print(traceback.format_exc(), flush=True)
        return ["tokenization failed"]

    try:
        embedding_connector.request_re_embed_records(
            project_id, prepped["embedding_rebuilds"]
        )

    except Exception as e:
        __revert_record_data_changes(records, prepped["record_data_backup"])
        print(traceback.format_exc(), flush=True)
        return ["embedding failed"]

    return None


def __revert_record_data_changes(
    records: Dict[str, Record], data_backup: Dict[str, Any]
) -> None:
    for record_id in data_backup:
        records[record_id].data = data_backup[record_id]
    general.commit()


def __check_and_prep_edit_records(
    project_id: str, changes: Dict[str, Any]
) -> Dict[str, Any]:
    # key example: <record_id>@<attribute_name>[@<sub_key>]

    errors_found = []  # list of strings
    useable_embeddings = {}  # dict of UUID(attribute_id): [embedding_item]
    attributes = None  # dict of attribute_name: attribute_item
    records = None  # dict of str(record_id): record_item
    record_data_backup = None  # dict of str(record_id): record_data
    embedding_rebuilds = {}  # dict of str(embedding_id): [str(record_id)]
    record_ids = {changes[key]["recordId"] for key in changes}
    attribute_names = {changes[key]["attributeName"] for key in changes}

    records = record.get_by_record_ids(project_id, record_ids)
    if len(record_ids) != len(records):
        errors_found.append("can't match record ids to project")
    records = {str(r.id): r for r in records}

    attributes = attribute.get_all_by_names(project_id, attribute_names)
    if len(attribute_names) != len(attributes):
        errors_found.append("can't match attributes to project")
    attributes = {a.name: a for a in attributes}

    tmp = [
        f"sub_key {changes[key]['subKey']} out of bounds for attribute {changes[key]['attributeName']} of record {changes[key]['recordId']}"
        for key in changes
        if "subKey" in changes[key]
        and changes[key]["subKey"]
        >= len(records[changes[key]["recordId"]].data[changes[key]["attributeName"]])
    ]

    if tmp and len(tmp) > 0:
        errors_found += tmp

    # note that queues for embeddings will not be checked since they are not yet run so uninteresting for us here
    embeddings = embedding.get_all_by_attribute_ids(
        project_id, [a.id for a in attributes.values()]
    )
    for embedding_item in embeddings:
        if embedding_item.state == enums.EmbeddingState.FAILED.value:
            # can be ignored since nothing exists to rebuild yet
            continue

        if embedding_item.state != enums.EmbeddingState.FINISHED.value:
            errors_found.append(
                f"embedding {embedding_item.name} is not finished. Wait for it to finish before editing records."
            )
            continue

        emb_path = os.path.join(
            "/inference", project_id, f"embedder-{str(embedding_item.id)}.pkl"
        )
        if not os.path.exists(emb_path):
            errors_found.append(
                f"can't find embedding PCA for {embedding_item.name}. Try rebuilding or removing the embeddings on settings page."
            )
            continue
        if not embedding_item.attribute_id in useable_embeddings:
            useable_embeddings[embedding_item.attribute_id] = []
        useable_embeddings[embedding_item.attribute_id].append(embedding_item)

    if tokenization.is_doc_bin_creation_running_or_queued(project_id):
        errors_found.append(
            "tokenization is currently running. Wait for it to finish before editing records."
        )

    if task_queue.get_by_tokenization(project_id) is not None:
        errors_found.append(
            "tokenization is currently queued. Wait for it to finish before editing records."
        )

    if errors_found:
        return {"errors_found": errors_found}

    record_data_backup = {str(r.id): copy.deepcopy(r.data) for r in records.values()}
    rla_delete_tuples = [
        (c["recordId"], str(attributes[c["attributeName"]].id))
        for c in changes.values()
        if "subKey" not in c
        and attributes[c["attributeName"]].data_type == enums.DataTypes.TEXT.value
    ]

    if len(useable_embeddings) > 0:
        for change in changes.values():
            attribute_id = attributes[change["attributeName"]].id
            if attribute_id not in useable_embeddings:
                continue
            for embedding_item in useable_embeddings[attribute_id]:
                embedding_id = str(embedding_item.id)
                if embedding_id not in embedding_rebuilds:
                    embedding_rebuilds[embedding_id] = []
                changed_record_info = {
                    "record_id": change["recordId"],
                    "attribute_name": change["attributeName"],
                }
                if "subKey" in change:
                    changed_record_info["sub_key"] = change["subKey"]
                embedding_rebuilds[embedding_id].append(changed_record_info)

    return {
        "records": records,
        "record_data_backup": record_data_backup,
        "rla_delete_tuples": rla_delete_tuples,
        "embedding_rebuilds": embedding_rebuilds,
    }
