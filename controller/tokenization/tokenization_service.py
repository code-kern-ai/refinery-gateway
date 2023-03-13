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


def request_tokenize_project(
    project_id: str,
    user_id: str,
    include_rats: bool = True,
    only_uploaded_attributes: bool = False,
) -> None:
    url = f"{BASE_URI}/tokenize_project"
    data = {
        "project_id": str(project_id),
        "record_id": "",
        "user_id": str(user_id),
        "include_rats": include_rats,
        "only_uploaded_attributes": only_uploaded_attributes,
    }
    service_requests.post_call_or_raise(url, data)


def request_tokenize_calculated_attribute(
    project_id: str, user_id: str, attribute_id: str, include_rats: bool = True
) -> None:
    url = f"{BASE_URI}/tokenize_calculated_attribute"
    data = {
        "project_id": str(project_id),
        "user_id": str(user_id),
        "attribute_id": str(attribute_id),
        "include_rats": include_rats,
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


def request_reupload_docbins(
    project_id: str,
) -> None:
    url = f"{BASE_URI}/reupload_docbins"
    data = {
        "project_id": str(project_id),
    }
    service_requests.post_call_or_raise(url, data)


def request_save_tokenizer(
    config_string: str,
) -> None:
    url = f"{BASE_URI}/save_tokenizer"
    data = {
        "config_string": config_string,
    }
    service_requests.post_call_or_raise(url, data)
