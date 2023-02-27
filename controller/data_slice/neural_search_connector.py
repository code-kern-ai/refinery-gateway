import os
from util import service_requests

BASE_URI = os.getenv("NEURAL_SEARCH")


def request_outlier_detection(project_id: str, embedding_id: str, limit: int):
    url = f"{BASE_URI}/detect_outliers"
    params = {
        "project_id": project_id,
        "embedding_id": embedding_id,
        "limit": limit,
    }
    return service_requests.get_call_or_raise(url, params)
