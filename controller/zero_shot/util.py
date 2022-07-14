import os
from util import service_requests
from typing import List, Any

BASE_URI = os.getenv("ZERO_SHOT")


def get_recommended_models() -> Any:
    url = f"{BASE_URI}/recommend"
    return service_requests.get_call_or_raise(url)


def start_zero_shot_for_project(
    project_id: str,
    payload_id: str,
) -> Any:
    url = f"{BASE_URI}/zero-shot/project"
    data = {
        "project_id": str(project_id),
        "payload_id": str(payload_id),
    }
    return service_requests.post_call_or_raise(url, data)


def get_zero_shot_text(
    project_id: str,
    information_source_id,
    config: str,
    text: str,
    run_individually: bool,
    label_names: List[str],
) -> Any:
    url = f"{BASE_URI}/zero-shot/text"
    data = {
        "project_id": project_id,
        "information_source_id": information_source_id,
        "config": config,
        "text": text,
        "run_individually": run_individually,
        "label_names": label_names,
    }
    return service_requests.post_call_or_raise(url, data)


def get_zero_shot_sample_records(
    project_id: str,
    information_source_id,
    label_names: List[str],
) -> Any:
    if label_names == None:
        label_names = []
    url = f"{BASE_URI}/zero-shot/sample-records"
    data = {
        "project_id": project_id,
        "information_source_id": information_source_id,
        "label_names": label_names,
    }
    return service_requests.post_call_or_raise(url, data)
