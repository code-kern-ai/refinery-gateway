from controller.attribute import manager
from controller.auth import manager as auth_manager
from typing import List, Union
from fast_api.models import DeleteUserAttributeBody, RunLlmPlaygroundBody
from fast_api.routes.client_response import pack_json_result, get_silent_success
from fastapi import APIRouter, Body, Depends, Query, Request
from submodules.model.enums import NotificationType
from submodules.model.util import sql_alchemy_to_dict
from util.notification import create_notification

router = APIRouter()

ALL_ATTRIBUTES_WHITELIST = {
    "id",
    "name",
    "data_type",
    "is_primary_key",
    "relative_position",
    "user_created",
    "source_code",
    "state",
    "logs",
    "visibility",
    "additional_config",
}


@router.get(
    "/{project_id}/all-attributes",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_attributes(
    project_id: str,
    state_filter: Union[List[str], None] = Query(default=None),
):
    data = manager.get_all_attributes(project_id, state_filter)
    data_dict = sql_alchemy_to_dict(data, column_whitelist=ALL_ATTRIBUTES_WHITELIST)
    # removes api key from llmConfig to prevent it from showing in the frontend
    for attr in data_dict:
        if attr.get("additional_config", {}) is None:
            continue
        attr.get("additional_config", {}).get("llmConfig", {}).pop("apiKey", None)
    return pack_json_result(data_dict)


@router.get(
    "/{project_id}/check-composite-key",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_check_composite_key(
    request: Request,
    project_id: str,
):
    user = auth_manager.get_user_by_info(request.state.info)
    is_valid = manager.check_composite_key(project_id)
    if not is_valid:
        create_notification(
            NotificationType.INVALID_PRIMARY_KEY,
            user.id,
            project_id,
        )

    return pack_json_result(is_valid)


@router.get(
    "/{project_id}/{attribute_id}/sample-records",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_sample_records(
    project_id: str,
    attribute_id,
):

    record_ids, calculated_attributes = manager.calculate_user_attribute_sample_records(
        project_id, attribute_id
    )
    return pack_json_result(
        {
            "record_ids": record_ids,
            "calculated_attributes": calculated_attributes,
        }
    )


@router.delete(
    "/{project_id}/delete-user-attribute",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_user_attribute(
    request: Request,
    project_id: str,
    body: DeleteUserAttributeBody = Body(...),
):
    manager.delete_attribute(project_id, body.attribute_id)
    return get_silent_success()


@router.post(
    "/{project_id}/{attribute_id}/run-llm-playground",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def run_llm_playground(
    request: Request,
    project_id,
    attribute_id,
    body: RunLlmPlaygroundBody = Body(...),
):
    return pack_json_result(
        manager.run_llm_playground(
            project_id,
            attribute_id,
            llm_playground_config=body.llm_config,
            record_ids=body.record_ids,
        ),
        wrap_for_frontend=False,
    )


@router.get(
    "/{project_id}/{attribute_id}/llm-ac-cache",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def llm_ac_cache(request: Request, project_id, attribute_id):
    return pack_json_result(
        manager.llm_ac_cache(project_id, attribute_id),
        wrap_for_frontend=False,
    )
