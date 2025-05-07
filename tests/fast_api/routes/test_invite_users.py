from fastapi.testclient import TestClient
from controller.auth.kratos import delete_user_kratos

from submodules.model.models import Organization
import requests
import time


def test_is_full_admin(client: TestClient):
    """
    Test validate user is an administrator

    Args:
        client (TestClient): The test client for making API requests.
    """
    response = client.get("/api/v1/misc/is-full-admin")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data is True


def test_valid_emails(client: TestClient):
    valid_emails_to_test = ["test@kern.ai", "devtools@kern.ai"]
    response = client.post(
        "/api/v1/misc/check-valid-emails",
        json={"emails": valid_emails_to_test},
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["allValid"] is True
    assert len(response_data["validEmails"]) == len(valid_emails_to_test)


def test_invalid_emails(client: TestClient):
    valid_emails_to_test = ["test@kern.ai", "devtools@kern.ai"]
    invalid_emails_to_test = ["test.kern.ai", "devtools@kern"]
    response = client.post(
        "/api/v1/misc/check-valid-emails",
        json={"emails": valid_emails_to_test + invalid_emails_to_test},
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["allValid"] is False
    assert len(response_data["validEmails"]) == len(valid_emails_to_test)


def test_invite_users(client: TestClient, org: Organization):
    requests.delete("http://mailhog:8025/api/v1/messages")
    valid_emails_to_test = ["test@kern.ai"]
    response = client.post(
        "/api/v1/misc/invite-users",
        json={"organization_name": org.name, "emails": valid_emails_to_test},
    )
    assert response.status_code == 200
    created_user_ids = response.json()

    email_response_data = {"total": 0}
    start_time = time.time()
    while email_response_data["total"] == 0 and time.time() - start_time < 5:
        email_response = requests.get(
            "http://mailhog:8025/api/v2/search",
            params={"kind": "to", "query": "test@kern.ai"},
        )
        email_response_data = email_response.json()
    assert email_response.status_code == 200

    for user_id in created_user_ids:
        delete_user_kratos(user_id)

    assert len(email_response_data["items"]) == len(valid_emails_to_test)
    assert email_response_data["total"] == len(valid_emails_to_test)
    assert email_response_data["count"] == len(valid_emails_to_test)
