import json
from controller.zero_shot import manager
from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from submodules.model.util import sql_alchemy_to_dict

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
