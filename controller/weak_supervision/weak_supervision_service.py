import os
from typing import Any

from util import notification, service_requests
from util.decorator import debounce

BASE_URI = os.getenv("WEAK_SUPERVISION")


def initiate_weak_supervision(
    project_id: str, labeling_task_id: str, user_id: str, weak_supervision_task_id: str
) -> Any:
    url = f"{BASE_URI}/fit_predict"
    data = {
        "project_id": str(project_id),
        "labeling_task_id": str(labeling_task_id),
        "user_id": str(user_id),
        "weak_supervision_task_id": str(weak_supervision_task_id),
    }
    return service_requests.post_call_or_raise(url, data)


def calculate_quality_after_labeling(
    project_id: str, labeling_task_id: str, user_id: str, source_id: str = None
) -> Any:
    if source_id is None:
        calculate_quality_after_labeling_reference(
            project_id, labeling_task_id, user_id
        )
    else:
        calculate_stats_after_source_run_with_debounce(project_id, source_id, user_id)


# for the same function parameter the function call is debounced for t seconds given as wait argument
# if for 5 sec nothing happens for the task the statistics are calculated
# since this is only relevant for changing record label associations as own function
@debounce(5)
def calculate_quality_after_labeling_reference(
    project_id: str, labeling_task_id: str, user_id: str
):
    url = f"{BASE_URI}/labeling_task_statistics"
    data = {
        "project_id": str(project_id),
        "labeling_task_id": str(labeling_task_id),
        "user_id": str(user_id),
    }
    return service_requests.post_call_or_raise(url, data)


def calculate_stats_after_source_run(
    project_id: str, source_id: str, user_id: str
) -> Any:
    url = f"{BASE_URI}/source_statistics"
    data = {
        "project_id": str(project_id),
        "source_id": str(source_id),
        "user_id": str(user_id),
    }
    return service_requests.post_call_or_raise(url, data)


@debounce(2)
def calculate_stats_after_source_run_with_debounce(
    project_id: str, source_id: str, user_id: str
):
    result = calculate_stats_after_source_run(project_id, source_id, user_id)
    notification.send_organization_update(
        project_id,
        f"model_callback_update_statistics:{source_id}",
    )
    return result
