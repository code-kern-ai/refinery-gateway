from controller.zero_shot import manager
from fast_api.models import (
    CancelZeroShotBody,
    CreateZeroShotBody,
    ZeroShot10Body,
    ZeroShotTextBody,
)
from fast_api.routes.client_response import pack_json_result
from controller.auth import manager as auth_manager
from fastapi import APIRouter, Body, Depends, Request
from controller.task_queue import manager as task_queue_manager
from controller.zero_shot import manager as zero_shot_manager
from submodules.model.enums import TaskType
from util import notification

router = APIRouter()


@router.get(
    "/{project_id}/zero-shot-recommendations",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_zero_shot_recommendations(
    request: Request,
    project_id: str,
):

    data = manager.get_zero_shot_recommendations(project_id)
    return pack_json_result({"data": {"zeroShotRecommendations": data}})


@router.post(
    "/{project_id}/zero-shot-text",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_zero_shot_text(
    request: Request,
    project_id: str,
    body: ZeroShotTextBody = Body(...),
):
    heuristic_id = body.heuristicId
    config = body.config
    text = body.text
    run_individually = body.runIndividually
    label_names = body.labelNames

    data = manager.get_zero_shot_text(
        project_id, heuristic_id, config, text, run_individually, label_names
    )
    final_data = {
        "config": data.config,
        "text": data.text,
        "labels": [
            {"labelName": label.label_name, "confidence": label.confidence}
            for label in data.labels
        ],
    }
    return {"data": {"zeroShotText": final_data}}


@router.post(
    "/{project_id}/zero-shot-10-records",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_zero_shot_10_records(
    request: Request,
    project_id: str,
    body: ZeroShot10Body = Body(...),
):
    heuristic_id = body.heuristicId
    label_names = body.labelNames

    data = manager.get_zero_shot_10_records(project_id, heuristic_id, label_names)
    final_data = {
        "duration": data.duration,
        "records": [
            {
                "recordId": record.record_id,
                "checkedText": record.checked_text,
                "fullRecordData": record.full_record_data,
                "labels": [
                    {"labelName": label.label_name, "confidence": label.confidence}
                    for label in record.labels
                ],
            }
            for record in data.records
        ],
    }
    return {"data": {"zeroShot10Records": final_data}}


@router.post(
    "/{project_id}/{heuristic_id}/run-zero-shot",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def init_zeroshot(
    request: Request,
    project_id: str,
    heuristic_id: str,
):
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    task_queue_manager.add_task(
        project_id,
        TaskType.INFORMATION_SOURCE,
        user_id,
        {
            "information_source_id": heuristic_id,
        },
    )
    return pack_json_result({"data": {"zeroShotProject": {"ok": True}}})


@router.post(
    "/{project_id}/create-zero-shot",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_zero_shot(
    request: Request,
    project_id: str,
    body: CreateZeroShotBody = Body(...),
):
    user = auth_manager.get_user_by_info(request.state.info)
    zero_shot_id = zero_shot_manager.create_zero_shot_information_source(
        user.id,
        project_id,
        body.target_config,
        body.labeling_task_id,
        body.attribute_id,
    )
    notification.send_organization_update(
        project_id, f"information_source_created:{zero_shot_id}"
    )
    return pack_json_result(
        {"data": {"createZeroShotInformationSource": {"id": zero_shot_id}}}
    )


@router.post(
    "/{project_id}/cancel-zero-shot",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def cancel_zero_shot(
    project_id: str,
    body: CancelZeroShotBody = Body(...),
):
    zero_shot_manager.cancel_zero_shot_run(
        project_id, body.heuristic_id, body.payload_id
    )
    return pack_json_result({"data": {"cancelZeroShot": {"ok": True}}})
