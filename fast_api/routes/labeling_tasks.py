from fast_api.models import (
    CreateLabelBody,
    CreateLabelingTaskBody,
    StringBody,
    UpdateLabelColorBody,
    UpdateLabelHotkeyBody,
    UpdateLabelNameBody,
    UpdateLabelingTaskBody,
    WarningDataBody,
)
from fastapi import APIRouter, Depends, Request, Body

from controller.auth import manager as auth_manager
from controller.labeling_task import manager as labeling_manager
from controller.project import manager as project_manager
from controller.labeling_task_label import manager as label_manager
from controller.labeling_task import manager as task_manager
from fast_api.routes.client_response import pack_json_result
from submodules.model import events
from util import notification


router = APIRouter()


@router.put(
    "/{project_id}/update-labeling-task",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_labeling_task(project_id: str, body: UpdateLabelingTaskBody = Body(...)):
    labeling_manager.update_labeling_task(
        project_id,
        body.labeling_task_id,
        body.labeling_task_target_id,
        body.labeling_task_name,
        body.labeling_task_type,
    )

    notification.send_organization_update(
        project_id,
        f"labeling_task_updated:{body.labeling_task_id}:{body.labeling_task_type}",
    )

    return pack_json_result({"data": {"updateLabelingTask": {"ok": True}}})


@router.delete(
    "/{project_id}/delete-labeling-task",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_labeling_task(project_id: str, body: StringBody = Body(...)):
    labeling_task_id = body.value
    labeling_manager.delete_labeling_task(project_id, labeling_task_id)

    notification.send_organization_update(
        project_id, f"labeling_task_deleted:{labeling_task_id}"
    )

    return pack_json_result({"data": {"deleteLabelingTask": {"ok": True}}})


@router.post(
    "/{project_id}/create-labeling-task",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_labeling_task(
    project_id: str, request: Request, body: CreateLabelingTaskBody = Body(...)
):
    item = labeling_manager.create_labeling_task(
        project_id,
        body.labeling_task_name,
        body.labeling_task_type,
        body.labeling_task_target_id,
    )

    notification.send_organization_update(
        project_id, f"labeling_task_created:{str(item.id)}"
    )

    return pack_json_result({"data": {"createLabelingTask": {"ok": True}}})


@router.delete(
    "/{project_id}/delete-label",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_label(project_id: str, body: StringBody = Body(...)):
    label_id = body.value
    label = label_manager.get_label(project_id, body.value)
    labeling_task_id = str(label.labeling_task_id)
    label_manager.delete_label(project_id, label_id)
    notification.send_organization_update(
        project_id, f"label_deleted:{label_id}:labeling_task:{labeling_task_id}"
    )

    return pack_json_result({"data": {"deleteLabel": {"ok": True}}})


@router.post(
    "/{project_id}/create-label",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_label(
    request: Request,
    project_id: str,
    body: CreateLabelBody = Body(...),
):
    label_name = body.labelName
    labeling_task_id = body.labelingTaskId
    label_color = body.labelColor

    if project_id:
        auth_manager.check_project_access(request.state.info, project_id)

    user = auth_manager.get_user_by_info(request.state.info)
    label = label_manager.create_label(
        project_id, label_name, labeling_task_id, label_color
    )
    notification.send_organization_update(
        project_id, f"label_created:{label.id}:labeling_task:{labeling_task_id}"
    )
    return pack_json_result({"data": {"createLabel": {"ok": True}}})


@router.put(
    "/{project_id}/update-label-color",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_label_color(project_id: str, body: UpdateLabelColorBody = Body(...)):
    label_manager.update_label_color(
        project_id, body.labeling_task_label_id, body.label_color
    )
    return pack_json_result({"data": {"updateLabelColor": {"ok": True}}})


@router.put(
    "/{project_id}/update-label-hotkey",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_label_hotkey(project_id: str, body: UpdateLabelHotkeyBody = Body(...)):
    label_manager.update_label_hotkey(
        project_id, body.labeling_task_label_id, body.label_hotkey
    )
    return pack_json_result({"data": {"updateLabelHotkey": {"ok": True}}})


@router.post(
    "/{project_id}/handle-label-rename-warnings",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def handle_label_rename_warnings(
    project_id: str,
    body: WarningDataBody = Body(...),
):
    label_manager.handle_label_rename_warning(project_id, body.warning_data)
    return pack_json_result({"data": {"handleLabelRenameWarnings": {"ok": True}}})


@router.put(
    "/{project_id}/update-label-name",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_label_name(
    project_id: str,
    body: UpdateLabelNameBody = Body(...),
):
    label_manager.update_label_name(project_id, body.label_id, body.new_name)
    return pack_json_result({"data": {"updateLabelName": {"ok": True}}})
