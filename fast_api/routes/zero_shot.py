import json
from controller.zero_shot import manager
from fast_api.routes.client_response import pack_json_result
from controller.auth import manager as auth_manager
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from submodules.model.util import sql_alchemy_to_dict
from controller.task_queue import manager as task_queue_manager
from submodules.model.enums import TaskType

router = APIRouter()


@router.get("/{project_id}/zero-shot-recommendations")
def get_zero_shot_recommendations(request: Request, project_id: str):

    data = manager.get_zero_shot_recommendations(project_id)
    return pack_json_result({"data": {"zeroShotRecommendations": data}})


@router.post("/{project_id}/zero-shot-text")
async def get_zero_shot_text(request: Request, project_id: str):
    body = await request.json()
    try:
        heuristic_id = body["heuristicId"]
        config = body["config"]
        text = body["text"]
        run_individually = body["runIndividually"]
        label_names = body["labelNames"]
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

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


@router.post("/{project_id}/zero-shot-10-records")
async def get_zero_shot_10_records(request: Request, project_id: str):
    body = await request.json()
    try:
        heuristic_id = body["heuristicId"]
        label_names = body["labelNames"]
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )
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


@router.post("/{project_id}/{heuristic_id}/run-zero-shot")
def init_zeroshot(request: Request, project_id: str, heuristic_id: str):
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
