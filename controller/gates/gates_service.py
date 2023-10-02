from typing import Dict, Any, List, Tuple, Optional
import requests
import os

BASE_URI = os.getenv("GATES_URI")


def start_gates_project(
    project_id: str, heuristics: List[str], embeddings: List[str]
) -> bool:
    url = BASE_URI + "/start-inference-api/" + str(project_id)
    response = requests.post(
        url,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
        },
        json={"heuristics": heuristics, "similarity_search": embeddings},
    )
    return response.status_code == 200


def stop_gates_project(project_id: str) -> bool:
    url = BASE_URI + "/stop-inference-api/" + str(project_id)
    response = requests.post(url)
    return response.status_code == 200


def call_gates_project(
    project_id: str, record_dict: Dict[str, Any], wait_on_pause: bool = True
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    url = BASE_URI + "/predict/project/" + str(project_id)

    if wait_on_pause:
        url += "?wait=true"
    response = requests.post(
        url,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
        },
        json=record_dict,
    )

    has_error, result, logs = False, None, None

    if response.status_code == 200:
        result = response.json()
    else:
        logs = [response.text]
        has_error = True
    return has_error, result, logs
