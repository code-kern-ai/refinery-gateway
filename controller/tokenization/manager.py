from typing import Any, List, Dict

import spacy
from spacy.tokens import DocBin
from controller.project import manager as project_manager
from submodules.model import enums, Record
from submodules.model.business_objects import tokenization, attribute
from submodules.model.business_objects.record import (
    get_tokenized_record_from_db,
    get_tokenized_records_from_db,
)
from util import daemon
from controller.tokenization import tokenization_service
from controller.tokenization.tokenization_service import (
    request_tokenize_record,
)
import logging
from controller.task_master import manager as task_master_manager
from submodules.model.enums import TaskType, RecordTokenizationScope

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
__blank_tokenizer_vocab = {}


# spacy needs the vocab of a blank spacy object to extract docs from doc_bins
# https://spacy.io/usage/saving-loading#docs


def get_blank_tokenizer_vocab(project_id: str) -> Any:
    project = project_manager.get_project(project_id)
    if not __blank_tokenizer_vocab.get(project.tokenizer_blank):
        __init_blank_tokenizer_vocab(project.tokenizer_blank)
    return __blank_tokenizer_vocab.get(project.tokenizer_blank)


def get_tokenized_record(project_id: str, record_id: str):
    # ensure docs are in db (prio queue)

    docs = __get_docs_from_db(project_id, record_id)
    tokenized_record = {}
    tokenized_record["record_id"] = record_id
    tokenized_record["attributes"] = []

    for attribute_name in docs:
        attribute_item = attribute.get_by_name(project_id, attribute_name)
        if attribute_item is None:
            # the docs could contain already deleted user created attributes
            continue

        tokenized_attribute = {}
        tokenized_attribute["raw"] = docs[attribute_name].text
        if attribute_item is not None and any(
            labeling_task.task_type
            == enums.LabelingTaskType.INFORMATION_EXTRACTION.value
            for labeling_task in attribute_item.labeling_tasks
        ):
            tokenized_attribute["tokens"] = [
                {
                    "value": token.text,
                    "idx": token.i,
                    "pos_start": token.idx,
                    "pos_end": token.idx + len(token),
                    "type": token.ent_type_,
                }
                for token in docs[attribute_name]
            ]
        tokenized_attribute["attribute"] = attribute_item
        tokenized_record["attributes"].append(tokenized_attribute)
    return tokenized_record


def create_rats_entries(project_id: str, user_id: str, attribute_id: str = "") -> None:
    tokenization_service.request_create_rats_entries(project_id, user_id, attribute_id)


def delete_token_statistics(records: List[Record]) -> None:
    tokenization.delete_token_statistics(records)


def delete_docbins(project_id: str, records: List[Record]) -> None:
    tokenization.delete_record_docbins(project_id, records)


def start_record_tokenization(project_id: str, record_id: str) -> None:
    daemon.run(
        request_tokenize_record,
        project_id,
        record_id,
    )


def start_project_tokenization(project_id: str, org_id: str, user_id: str) -> None:
    task_master_manager.queue_task(
        str(org_id),
        str(user_id),
        TaskType.TOKENIZATION,
        {
            "scope": RecordTokenizationScope.PROJECT.value,
            "include_rats": True,
            "only_uploaded_attributes": False,
            "project_id": str(project_id),
        },
    )


def __get_docs_from_db(project_id: str, record_id: str) -> Dict[str, Any]:
    vocab = get_blank_tokenizer_vocab(project_id)

    table_entry = get_tokenized_record_from_db(project_id, record_id)
    if not table_entry:
        tokenization_service.request_tokenize_record(project_id, record_id)
        table_entry = get_tokenized_record_from_db(project_id, record_id)

    doc_bin_loaded = DocBin().from_bytes(table_entry.bytes)
    docs = list(doc_bin_loaded.get_docs(vocab))
    doc_dict = {}
    for col, doc in zip(table_entry.columns, docs):
        doc_dict[col] = doc
    return doc_dict


def get_all_docs_from_db(
    project_id: str, record_ids: List[str]
) -> Dict[str, Dict[str, Any]]:
    vocab = get_blank_tokenizer_vocab(project_id)
    table_entries = get_tokenized_records_from_db(project_id, record_ids)
    doc_dict = {}
    for table_entry in table_entries:
        record_id = str(table_entry.record_id)
        doc_bin_loaded = DocBin().from_bytes(table_entry.bytes)
        docs = list(doc_bin_loaded.get_docs(vocab))
        for col, doc in zip(table_entry.columns, docs):
            if record_id not in doc_dict:
                doc_dict[record_id] = {}
            if not doc_dict.get(record_id):
                doc_dict[record_id] = {}
            doc_dict[record_id][col] = doc
    return doc_dict


def get_token_dict_for_records(
    project_id: str, record_ids: List[str]
) -> Dict[str, Dict[str, List[int]]]:
    # record_id -> attribute_name -> [ {start:token.idx, end:token.idx + len(token)}]
    doc_dict = get_all_docs_from_db(project_id, record_ids)
    return {
        record_id: {
            attribute_name: [
                {"start": token.idx, "end": token.idx + len(token)}
                for token in doc_dict[record_id][attribute_name]
            ]
            for attribute_name in doc_dict[record_id]
        }
        for record_id in doc_dict
    }


def __init_blank_tokenizer_vocab(language: str) -> None:
    __blank_tokenizer_vocab[language] = spacy.blank(language).vocab
