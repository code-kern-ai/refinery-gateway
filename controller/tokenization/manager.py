from typing import Any, List, Dict

import spacy
from spacy.tokens import DocBin
from controller.project import manager as project_manager
from graphql_api.types import TokenizedRecord, TokenizedAttribute, TokenWrapper
from submodules.model import enums, Record
from graphql_api import types
from submodules.model.business_objects import tokenization, attribute
from submodules.model.business_objects.record import __get_tokenized_record
from util import daemon
from controller.tokenization import tokenization_service
from controller.tokenization.tokenization_service import (
    request_tokenize_project,
    request_tokenize_record,
)
import logging

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


def get_tokenized_record(
    project_id: str, record_id: str
) -> TokenizedRecord:
    # ensure docs are in db (prio queue)

    docs = __get_docs_from_db(project_id, record_id)
    tokenized_record = TokenizedRecord()
    tokenized_record.record_id = record_id
    tokenized_record.attributes = []

    for attribute_name in docs:
        attribute_item = attribute.get_by_name(project_id, attribute_name)

        tokenized_attribute = TokenizedAttribute()
        tokenized_attribute.raw = docs[attribute_name].text
        if attribute_item is not None and any(
            labeling_task.task_type
            == enums.LabelingTaskType.INFORMATION_EXTRACTION.value
            for labeling_task in attribute_item.labeling_tasks
        ):
            tokenized_attribute.tokens = [
                TokenWrapper(
                    value=token.text,
                    idx=token.i,
                    pos_start=token.idx,
                    pos_end=token.idx + len(token),
                    type=token.ent_type_,
                )
                for token in docs[attribute_name]
            ]
        tokenized_attribute.attribute = attribute_item
        tokenized_record.attributes.append(tokenized_attribute)
    return tokenized_record


def create_rats_entries(project_id: str, user_id: str, attribute_id: str) -> None:
    attribute_id = attribute_id if attribute_id else ""
    tokenization_service.request_create_rats_entries(project_id, user_id, attribute_id)


def delete_token_statistics(records: List[Record]) -> None:
    tokenization.delete_token_statistics(records)


def delete_docbins(project_id: str, records: List[Record]) -> None:
    tokenization.delete_record_docbins(project_id, records)


def start_record_tokenization(project_id: str, record_id: str) -> None:
    daemon.run(
        request_tokenize_record, project_id, record_id,
    )


def start_project_tokenization(project_id: str, user_id: str) -> None:
    daemon.run(
        request_tokenize_project, project_id, user_id,
    )


def __get_docs_from_db(project_id: str, record_id: str) -> Dict[str, Any]:
    vocab = get_blank_tokenizer_vocab(project_id)

    table_entry = __get_tokenized_record(project_id, record_id)
    if not table_entry:
        tokenization_service.request_tokenize_record(project_id, record_id)
        table_entry = __get_tokenized_record(project_id, record_id)

    doc_bin_loaded = DocBin().from_bytes(table_entry.bytes)
    docs = list(doc_bin_loaded.get_docs(vocab))
    doc_dict = {}
    for (col, doc) in zip(table_entry.columns, docs):
        doc_dict[col] = doc
    return doc_dict


def __init_blank_tokenizer_vocab(language: str) -> None:
    __blank_tokenizer_vocab[language] = spacy.blank(language).vocab
