import os

from util import service_requests

BASE_URI = os.getenv("TOKENIZER")


def request_tokenize_record(project_id: str, record_id: str) -> None:
    url = f"{BASE_URI}/tokenize_record"
    data = {
        "project_id": str(project_id),
        "record_id": str(record_id),
        "user_id": "",
    }
    service_requests.post_call_or_raise(url, data)


def request_tokenize_project(project_id: str, user_id: str) -> None:
    url = f"{BASE_URI}/tokenize_project"
    data = {
        "project_id": str(project_id),
        "record_id": "",
        "user_id": str(user_id),
    }
    service_requests.post_call_or_raise(url, data)


# rats is the abbreviation of the table record_attribute_token_statistics
def request_create_rats_entries(
    project_id: str, user_id: str, attribute_id: str
) -> None:
    url = f"{BASE_URI}/create_rats"
    data = {
        "project_id": str(project_id),
        "user_id": str(user_id),
        "attribute_id": str(attribute_id),
    }
    service_requests.post_call_or_raise(url, data)
