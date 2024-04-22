from fastapi.testclient import TestClient
from submodules.model.models import Project as RefineryProject

from submodules.model.business_objects import general


def test_get_project_by_project_id(
    client: TestClient, refinery_project: RefineryProject
):
    response = client.get(
        f"/api/v1/project/{refinery_project.id}/project-by-project-id"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data.get("data")
    assert response_data["data"].get("projectByProjectId")
    assert response_data["data"]["projectByProjectId"].get("id")


def test_update_project_name_description(
    client: TestClient, refinery_project: RefineryProject
):
    response = client.post(
        f"/api/v1/project/{refinery_project.id}/update-project-name-description",
        json={"name": "new_name", "description": "new_description"},
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data.get("data")
    assert response_data["data"].get("updateProjectNameDescription")
    assert response_data["data"]["updateProjectNameDescription"].get("ok")

    general.refresh(refinery_project)
    assert refinery_project.name == "new_name"
    assert refinery_project.description == "new_description"
