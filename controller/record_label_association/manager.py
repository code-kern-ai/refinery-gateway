from typing import List, Optional
from submodules.model.exceptions import EntityNotFoundException
from util import notification
import json


from submodules.model import enums, RecordLabelAssociation, Record
from submodules.model.business_objects import (
    record,
    record_label_association,
    labeling_task_label,
    labeling_task,
    general,
)
from submodules.model.business_objects.record_label_association import (
    check_label_duplication_classification,
    get_project_ids_with_rlas,
    get_labeling_tasks_from_ids,
    update_is_relevant_manual_label,
    update_is_valid_manual_label_for_project,
)
from util import daemon
from controller.weak_supervision import weak_supervision_service as weak_supervision
from controller.knowledge_term import manager as term_manager
from controller.information_source import manager as information_source_manager
from controller.payload import manager as payload_manager
from controller.data_slice import manager as data_slice_manager


def get_last_annotated_record_id(
    project_id: str, top_n: int
) -> List[RecordLabelAssociation]:
    return record_label_association.get_latest(project_id, top_n)


def is_any_record_manually_labeled(project_id: str):
    return record_label_association.is_any_record_manually_labeled(project_id)


def __infer_source_type(source_id: str, project_id: str):
    if source_id is not None:
        source = information_source_manager.get_information_source(
            project_id, source_id
        )
        if source is None:
            raise EntityNotFoundException("Information source not found")
        label_source_type = enums.LabelSource.INFORMATION_SOURCE.value
    else:
        label_source_type = enums.LabelSource.MANUAL.value
    return label_source_type


def update_annotator_progress(project_id: str, source_id: str, user_id: str):
    information_source = information_source_manager.get_information_source(
        project_id, source_id
    )

    if len(information_source.payloads) == 0:
        payload = payload_manager.create_empty_crowd_payload(
            project_id, source_id, user_id
        )
    else:
        payload = information_source.payloads[0]

    details = json.loads(information_source.source_code)
    data_slice_id = details["data_slice_id"]
    annotator_id = details["annotator_id"]
    percentage = record_label_association.get_percentage_of_labeled_records_for_slice(
        project_id,
        annotator_id,
        data_slice_id,
        str(information_source.labeling_task_id),
    )
    payload_manager.update_payload_progress(project_id, payload.id, percentage)

    if percentage == 1:
        payload_manager.update_payload_status(
            project_id,
            payload.id,
            enums.PayloadState.FINISHED.value,
        )
    general.commit()
    notification.send_organization_update(
        project_id, f"information_source_updated:{str(information_source.id)}"
    )


def create_manual_classification_label(
    project_id: str,
    user_id: str,
    record_id: str,
    label_id: str,
    labeling_task_id: str,
    as_gold_star: Optional[bool] = None,
    source_id: str = None,
    confidence: float = 1.0,
) -> Record:
    if not as_gold_star:
        as_gold_star = None

    record_item = record.get(project_id, record_id)
    if record_item is None:
        return None

    label_source_type = __infer_source_type(source_id, project_id)

    label_ids = labeling_task_label.get_all_ids_query(project_id, labeling_task_id)
    record_label_association.delete(
        project_id,
        record_id,
        user_id,
        label_ids,
        as_gold_star,
        source_id,
        label_source_type,
        with_commit=True,
    )
    record_label_association.create(
        project_id=project_id,
        record_id=record_id,
        labeling_task_label_id=label_id,
        created_by=user_id,
        source_type=label_source_type,
        return_type=enums.InformationSourceReturnType.RETURN.value,
        is_gold_star=as_gold_star,
        source_id=source_id,
        with_commit=True,
        confidence=confidence,
    )
    if label_source_type == enums.LabelSource.INFORMATION_SOURCE.value:
        update_annotator_progress(project_id, source_id, user_id)
    daemon.run(
        weak_supervision.calculate_quality_after_labeling,
        project_id,
        labeling_task_id,
        user_id,
        source_id,
    )
    update_is_relevant_manual_label(
        project_id, labeling_task_id, record_id, with_commit=True
    )
    if not as_gold_star:
        label_ids = [str(row.id) for row in label_ids.all()]
        daemon.run(
            __check_label_duplication_classification_and_react,
            project_id,
            record_id,
            user_id,
            label_ids,
        )
    return record_item


def __check_label_duplication_classification_and_react(
    project_id: str, record_id: str, user_id: str, label_ids: List[str]
):
    if check_label_duplication_classification(
        project_id, record_id, user_id, label_ids
    ):

        notification.send_organization_update(project_id, f"rla_deleted:{record_id}")


def create_manual_extraction_label(
    project_id: str,
    user_id: str,
    record_id: str,
    labeling_task_id: str,
    label_id: str,
    token_start_index: int,
    token_end_index: int,
    value: str,
    as_gold_star: Optional[bool] = None,
    source_id: str = None,
    confidence: float = 1.0,
) -> Record:
    if not as_gold_star:
        as_gold_star = None

    label_item = labeling_task_label.get(project_id, label_id)
    record_item = record.get(project_id, record_id)

    if label_item is None:
        return None
    label_source_type = __infer_source_type(source_id, project_id)

    new_tokens = record_label_association.create_token_objects(
        project_id, token_start_index, token_end_index + 1
    )
    l = record_label_association.create(
        project_id,
        record_id,
        label_id,
        user_id,
        label_source_type,
        enums.InformationSourceReturnType.YIELD.value,
        as_gold_star,
        new_tokens,
        source_id=source_id,
        with_commit=True,
        confidence=confidence,
    )
    update_is_relevant_manual_label(
        project_id, labeling_task_id, record_id, with_commit=True
    )
    if label_source_type == enums.LabelSource.MANUAL.value:
        term_manager.create_term_in_named_knowledge_base(
            project_id, label_item.name, value
        )
    if label_source_type == enums.LabelSource.INFORMATION_SOURCE.value:
        update_annotator_progress(project_id, source_id, user_id)
    daemon.run(
        weak_supervision.calculate_quality_after_labeling,
        project_id,
        labeling_task_id,
        user_id,
        source_id,
    )
    return record_item


def create_gold_star_association(
    project_id: str,
    record_id: str,
    labeling_task_id: str,
    gold_user_id: str,
    user_id: str,
) -> str:
    if gold_user_id == "NULL":
        gold_user_id = None

    # grad add data
    task = labeling_task.get(project_id, labeling_task_id)
    task_type = task.task_type

    label_ids = labeling_task_label.get_all_ids_query(project_id, labeling_task_id)
    record_label_association.delete(
        project_id, record_id, user_id, label_ids, True, with_commit=True
    )

    associations = record_label_association.get_all_with_filter(
        project_id,
        record_id,
        labeling_task_id,
        enums.LabelSource.MANUAL.value,
        gold_user_id,
    )

    if task_type == enums.LabelingTaskType.CLASSIFICATION.value:
        record_label_association.create_gold_classification_association(
            associations, user_id, with_commit=True
        )
    elif task_type == enums.LabelingTaskType.INFORMATION_EXTRACTION.value:
        record_label_association.create_gold_extraction_association(
            associations, user_id, with_commit=True
        )
    else:
        raise ValueError(f"Can't set gold star for task_type {task_type}")

    update_is_relevant_manual_label(project_id, labeling_task_id, record_id)
    return task_type


def update_is_valid_manual_label_for_all() -> None:
    project_ids = get_project_ids_with_rlas()
    for project_id in project_ids:
        update_is_valid_manual_label_for_project(project_id)
    general.commit()


def delete_record_label_association(
    project_id: str, record_id: str, association_ids: List[str], user_id: str
) -> None:
    source_ids = record_label_association.check_any_id_is_source_related(
        project_id, record_id, association_ids
    )
    task_ids = get_labeling_tasks_from_ids(project_id, association_ids)
    record_label_association.delete_by_ids(
        project_id, association_ids, record_id, with_commit=True
    )
    for task_id in task_ids:
        update_is_relevant_manual_label(project_id, task_id, record_id)
    general.commit()
    if source_ids:
        for s_id in source_ids:
            update_annotator_progress(project_id, s_id, user_id)


def delete_gold_star_association(
    project_id: str, user_id: str, record_id: str, labeling_task_id: str
) -> None:
    label_ids = labeling_task_label.get_all_ids_query(project_id, labeling_task_id)
    record_label_association.delete(
        project_id, record_id, user_id, label_ids, True, with_commit=True
    )
    update_is_relevant_manual_label(
        project_id, labeling_task_id, record_id, with_commit=True
    )
