from fastapi import APIRouter, Depends, Request, Body
from controller.weak_supervision import manager
from controller.auth import manager as auth_manager
from fast_api.models import InitWeakSuperVisionBody, RunThenWeakSupervisionBody
from fast_api.routes.client_response import pack_json_result

router = APIRouter()


@router.post(
    "/{project_id}", dependencies=[Depends(auth_manager.check_project_access_dep)]
)
def init_weak_supervision(
    request: Request,
    project_id: str,
    init_body: InitWeakSuperVisionBody = Body(...),
):
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    manager.run_weak_supervision(
        project_id,
        user_id,
        init_body.overwrite_default_precision,
        init_body.overwrite_weak_supervision,
    )

    return pack_json_result(
        {"data": {"initiateWeakSupervisionByProjectId": {"ok": True}}}
    )


@router.post(
    "/{project_id}/run-then-weak-supervision",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def run_then_weak_supervision(
    request: Request,
    project_id: str,
    body: RunThenWeakSupervisionBody = Body(...),
):
    user_id = auth_manager.get_user_by_info(request.state.info).id
    manager.run_then_weak_supervision(
        project_id, body.heuristic_id, user_id, body.labeling_task_id
    )
    return pack_json_result({"data": {"runThenWeakSupervision": {"ok": True}}})
