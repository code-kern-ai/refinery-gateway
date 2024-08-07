from controller.attribute import manager as attribute_manager
from controller.zero_shot import manager as zero_shot_manager
from controller.payload import manager as payload_manager
from controller.data_slice import manager as data_slice_manager
from fast_api.models import (
    AttributeCalculationTaskExecutionBody,
    InformationSourceTaskExecutionBody,
    DataSliceActionExecutionBody,
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
    project_id = information_source_task_execution.project_id
    information_source_id = information_source_task_execution.information_source_id
    information_source_type = information_source_task_execution.information_source_type
    user_id = information_source_task_execution.user_id
    # already threaded in managers
    if information_source_type == InformationSourceType.ZERO_SHOT.value:
        payload_id = zero_shot_manager.start_zero_shot_for_project_thread(
            project_id, information_source_id, user_id
        )
    else:
        payload_id = payload_manager.create_payload(
            project_id, information_source_id, user_id
        )

    return pack_json_result({"payload_id": payload_id})


@router.post(
    "/data-slice",
)
def data_slice(
    data_slice_action_execution: DataSliceActionExecutionBody,
):
    project_id = data_slice_action_execution.project_id
    embedding_id = data_slice_action_execution.embedding_id
    user_id = data_slice_action_execution.user_id

    daemon.run(
        data_slice_manager.create_outlier_slice, project_id, user_id, str(embedding_id)
    )

    return SILENT_SUCCESS_RESPONSE
