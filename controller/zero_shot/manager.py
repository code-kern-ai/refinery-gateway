import datetime
import json
import timeit

from typing import List, Dict, Optional

from graphql_api.types import (
    ZeroShotTextResult,
    LabelConfidenceWrapper,
    ZeroShotNRecordsWrapper,
    ZeroShotNRecords,
)
from . import util as zs_service
from submodules.model import enums
from submodules.model.business_objects import (
    general,
    record,
    information_source,
    labeling_task,
    payload,
    project,
)
from util import daemon
from controller.weak_supervision import weak_supervision_service as weak_supervision
from controller.model_provider import manager as model_manager
from controller.misc import manager as misc


def get_zero_shot_text(
    project_id: str,
    information_source_id: str,
    config: str,
    text: str,
    run_individually: bool,
    label_names: List[str],
) -> ZeroShotTextResult:
    zero_shot_results = zs_service.get_zero_shot_text(
        project_id, information_source_id, config, text, run_individually, label_names
    )
    labels = [
        LabelConfidenceWrapper(label_name=row[0], confidence=row[1])
        for row in zero_shot_results
    ]
    return ZeroShotTextResult(config=config, text=text, labels=labels)


def get_zero_shot_recommendations(
    project_id: Optional[str] = None,
) -> List[Dict[str, str]]:
    recommendations = zs_service.get_recommended_models()
    if misc.check_is_managed():
        existing_models = model_manager.get_model_provider_info()
    else:
        existing_models = []

    for model in existing_models:
        if model["zero_shot_pipeline"]:
            not_existing_yet = (
                len(
                    list(
                        filter(
                            lambda rec: rec["configString"] == model["name"],
                            recommendations,
                        )
                    )
                )
                == 0
            )
            if not_existing_yet:
                recommendations.append(
                    {
                        "configString": model["name"],
                        "avgTime": "n/a",
                        "language": "n/a",
                        "link": model["link"],
                        "base": "n/a",
                        "size": __format_size_string(model["size"]),
                        "prio": 1,
                    }
                )

    if not project_id:
        return recommendations

    project_item = project.get(project_id)
    if project_item and project_item.tokenizer_blank:
        recommendations = [
            r
            for r in recommendations
            if r["language"] == project_item.tokenizer_blank or r["language"] == "n/a"
        ]
    return recommendations


def get_zero_shot_10_records(
    project_id: str, information_source_id: str, label_names: Optional[List[str]] = None
) -> ZeroShotNRecordsWrapper:
    start = timeit.default_timer()
    result = zs_service.get_zero_shot_sample_records(
        project_id, information_source_id, label_names
    )
    result_records = [
        (
            ZeroShotNRecords(
                record_id=record_item.get("record_id"),
                checked_text=record_item.get("checked_text"),
                full_record_data=record_item.get("full_record_data"),
                labels=[
                    LabelConfidenceWrapper(
                        label_name=label.get("label_name"),
                        confidence=label.get("confidence"),
                    )
                    for label in record_item.get("labels")
                ],
            )
        )
        for record_item in result
    ]
    return ZeroShotNRecordsWrapper(
        duration=timeit.default_timer() - start, records=result_records
    )


def create_zero_shot_information_source(
    user_id: str,
    project_id: str,
    target_config: str,
    labeling_task_id: str,
    attribute_id: str,
) -> str:
    return_type = enums.InformationSourceReturnType.RETURN.value
    labeling_task_item = labeling_task.get(project_id, labeling_task_id)
    if not attribute_id:
        attribute_id = str(labeling_task_item.attribute_id)

    current_labels = len(labeling_task_item.labels)
    if current_labels <= 0:
        default_confidence = 0.5
    else:
        default_confidence = round(min((1 / current_labels) + 0.2, 0.8), 1)

    zero_shot_default_parameter = {
        "config": target_config,
        "attribute_id": attribute_id,
        "min_confidence": default_confidence,
        "excluded_labels": [],
        "run_individually": False,
    }
    zero_shot_default_parameter = json.dumps(zero_shot_default_parameter)
    task = labeling_task.get(project_id, labeling_task_id)
    description = "Zero shot module for "
    if task:
        description += task.name
    else:
        description += "unknown"

    zero_shot = information_source.create(
        project_id=project_id,
        name="Zero Shot Classification",
        labeling_task_id=labeling_task_id,
        source_code=zero_shot_default_parameter,
        description=description,
        type=enums.InformationSourceType.ZERO_SHOT.value,
        return_type=return_type,
        created_by=user_id,
        with_commit=True,
    )

    return str(zero_shot.id)


def start_zero_shot_for_project_thread(
    project_id: str, information_source_id: str, user_id: str
) -> str:
    zero_shot_is = information_source.get(project_id, information_source_id)

    if not zero_shot_is:
        raise ValueError("unknown information source:" + information_source_id)
    iteration = len(zero_shot_is.payloads) + 1

    new_payload = payload.create(
        project_id,
        zero_shot_is.source_code,
        enums.PayloadState.CREATED,
        iteration,
        information_source_id,
        user_id,
        datetime.datetime.now(),
        with_commit=True,
    )
    payload_id = str(new_payload.id)
    daemon.run(
        __start_zero_shot_for_project,
        project_id,
        information_source_id,
        user_id,
        payload_id,
    )
    return payload_id


def __start_zero_shot_for_project(
    project_id: str, information_source_id: str, user_id: str, payload_id: str
) -> None:
    zs_service.start_zero_shot_for_project(project_id, payload_id)
    ctx_token = general.get_ctx_token()

    # refetch after service call
    new_payload = payload.get(project_id, payload_id)
    if new_payload.state == enums.PayloadState.FINISHED.value:
        new_payload.finished_at = datetime.datetime.now()
        general.commit()
    general.remove_and_refresh_session(ctx_token)
    try:
        weak_supervision.calculate_stats_after_source_run(
            project_id, information_source_id, user_id
        )
    except:
        print(
            f"Can't calculate stats for zero shot project {project_id}, is {information_source_id}",
            flush=True,
        )


def cancel_zero_shot_run(
    project_id: str,
    information_source_id: str,
    payload_id: str,
) -> None:
    item = information_source.get_payload(project_id, payload_id)
    if not item:
        raise ValueError("unknown payload:" + payload_id)
    if str(item.source_id) != information_source_id:
        raise ValueError("payload does not belong to information source")
    # setting the state to failed with be noted by the thread in zs service and handled
    item.state = enums.PayloadState.FAILED.value
    general.commit()


def __format_size_string(size: int) -> str:
    size_in_mb = int(size / 1048576)

    if size_in_mb < 1024:
        return str(size_in_mb) + " MB"
    else:
        return str(size_in_mb / 1024) + " GB"
