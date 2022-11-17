from typing import Any, Dict, List, Optional, Tuple
from controller.payload import payload_scheduler
from graphql_api.types import (
    LabelingFunctionSampleRecordWrapper,
    LabelingFunctionSampleRecords,
)
from submodules.model import InformationSourcePayload, enums
from submodules.model.business_objects import information_source, payload


def get_payload(project_id: str, payload_id: str) -> InformationSourcePayload:
    return payload.get(project_id, payload_id)


def create_payload(
    info,
    project_id: str,
    information_source_id: str,
    user_id: str,
    asynchronous: Optional[bool] = True,
) -> InformationSourcePayload:
    information_source_item = information_source.get(project_id, information_source_id)
    if information_source_item.type == enums.InformationSourceType.CROWD_LABELER:
        return None
    return payload_scheduler.create_payload(
        info, project_id, information_source_id, user_id, asynchronous
    )


def create_empty_crowd_payload(
    project_id: str, information_source_id: str, user_id: str
) -> InformationSourcePayload:
    return payload.create_empty_crowd_payload(
        project_id, information_source_id, user_id
    )


def update_payload_progress(
    project_id: str, payload_id: str, progress: float
) -> InformationSourcePayload:
    return payload.update_progress(project_id, payload_id, progress)


def update_payload_status(
    project_id: str, payload_id: str, status: str
) -> InformationSourcePayload:
    return payload.update_status(project_id, payload_id, status)


def get_labeling_function_on_10_records(
    project_id: str, information_source_id: str
) -> LabelingFunctionSampleRecords:
    doc_bin_samples, sample_records = payload_scheduler.prepare_sample_records_doc_bin(
        project_id=project_id, information_source_id=information_source_id
    )
    (
        calculated_labels,
        container_logs,
        code_has_errors,
    ) = payload_scheduler.run_labeling_function_exec_env(
        project_id=project_id,
        information_source_id=information_source_id,
        prefixed_doc_bin=doc_bin_samples,
    )
    calculated_labels = fill_missing_record_ids(sample_records, calculated_labels)

    return LabelingFunctionSampleRecords(
        records=[
            LabelingFunctionSampleRecordWrapper(
                record_id=record_item[0],
                full_record_data=record_item[1],
                calculated_labels=calculated_labels[record_item[0]],
            )
            for record_item in sample_records
        ],
        container_logs=container_logs,
        code_has_errors=code_has_errors,
    )


def fill_missing_record_ids(
    sample_records: List[str], calculated_labels: Dict[str, List[Any]]
) -> List[str]:
    for record_item in sample_records:
        record_id = record_item[0]
        if record_id not in calculated_labels:
            calculated_labels[record_id] = []

    return calculated_labels
