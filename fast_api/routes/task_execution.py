from controller.attribute import manager as attribute_manager
from controller.zero_shot import manager as zero_shot_manager
from controller.payload import manager as payload_manager
from controller.data_slice import manager as data_slice_manager
from controller.weak_supervision import manager as weak_supervision_manager
from fast_api.models import (
    AttributeCalculationTaskExecutionBody,
    InformationSourceTaskExecutionBody,
    DataSliceActionExecutionBody,
    WeakSupervisionActionExecutionBody,
)
from fastapi import APIRouter
from util import daemon
from submodules.model.enums import InformationSourceType
from fast_api.routes.client_response import pack_json_result, SILENT_SUCCESS_RESPONSE

router = APIRouter()


@router.post(
    "/attribute-calculation",
)
def calculate_attributes(
    attribute_calculation_task_execution: AttributeCalculationTaskExecutionBody,
):
    # REMOVE BEFORE MERGE
    return
    daemon.run(
        attribute_manager.calculate_user_attribute_all_records,
        attribute_calculation_task_execution.project_id,
        attribute_calculation_task_execution.organization_id,
        attribute_calculation_task_execution.user_id,
        attribute_calculation_task_execution.attribute_id,
    )

    return SILENT_SUCCESS_RESPONSE


@router.post(
    "/information-source",
)
def information_source(
    information_source_task_execution: InformationSourceTaskExecutionBody,
):

    # already threaded in managers
    if (
        information_source_task_execution.information_source_type
        == InformationSourceType.ZERO_SHOT.value
    ):
        payload_id = zero_shot_manager.start_zero_shot_for_project_thread(
            information_source_task_execution.project_id,
            information_source_task_execution.information_source_id,
            information_source_task_execution.user_id,
        )
    else:
        payload = payload_manager.create_payload(
            information_source_task_execution.project_id,
            information_source_task_execution.information_source_id,
            information_source_task_execution.user_id,
        )
        if payload:
            payload_id = payload.id
    return pack_json_result({"payload_id": str(payload_id)}, wrap_for_frontend=False)


@router.post(
    "/data-slice",
)
def data_slice(
    data_slice_action_execution: DataSliceActionExecutionBody,
):

    daemon.run(
        data_slice_manager.create_outlier_slice,
        data_slice_action_execution.project_id,
        data_slice_action_execution.user_id,
        data_slice_action_execution.embedding_id,
    )

    return SILENT_SUCCESS_RESPONSE


@router.post(
    "/weak-supervision",
)
def weak_supervision(
    weak_supervision_action_execution: WeakSupervisionActionExecutionBody,
):

    daemon.run(
        weak_supervision_manager.run_weak_supervision,
        weak_supervision_action_execution.project_id,
        weak_supervision_action_execution.user_id,
    )

    return SILENT_SUCCESS_RESPONSE
