from fastapi.testclient import TestClient
from submodules.model.models import Project as RefineryProject, User

from controller.transfer import record_transfer_manager
from api import transfer as transfer_api
from controller.upload_task import manager as upload_task_manager
from submodules.model.business_objects import (
    general,
    record as record_bo,
    attribute as attribute_bo,
    embedding as embedding_bo,
)
from submodules.model import enums
import json
import time


def test_get_project_by_project_id(
    client: TestClient, refinery_project: RefineryProject
):
    response = client.get(
        f"/api/v1/project/{refinery_project.id}/project-by-project-id"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data.get("id")


def test_update_project_name_description(
    client: TestClient, refinery_project: RefineryProject
):
    response = client.post(
        f"/api/v1/project/{refinery_project.id}/update-project-name-description",
        json={"name": "new_name", "description": "new_description"},
    )
    assert response.status_code == 200

    general.refresh(refinery_project)
    assert refinery_project.name == "new_name"
    assert refinery_project.description == "new_description"


def test_upload_records_to_project(
    client: TestClient, refinery_project: RefineryProject, user: User
):
    upload_task = upload_task_manager.create_upload_task(
        str(user.id),
        str(refinery_project.id),
        "dummy_file_name.csv",
        "records",
        "",
        upload_type=enums.UploadTypes.DEFAULT.value,
        key=None,
    )
    record_transfer_manager.import_file_record_dict(
        refinery_project.id,
        upload_task,
        [
            {"running_id": 1, "data": "hello world"},
            {"running_id": 2, "data": "hello world 2"},
        ],
    )

    assert record_bo.count(refinery_project.id) == 2
    attributes = attribute_bo.get_all(project_id=refinery_project.id)
    assert len(attributes) == 2

    for attribute in attributes:
        if attribute.name != "running_id":
            continue
        att = attribute_bo.update(
            refinery_project.id, attribute.id, is_primary_key=True, with_commit=True
        )
    assert att is not None
    assert att.is_primary_key is True


## in same file to ensure it's run in correct order
def test_create_embedding(client: TestClient, refinery_project: RefineryProject):

    att = attribute_bo.get_by_name(refinery_project.id, "data")

    assert att is not None

    response = client.post(
        f"/api/v1/embedding/{refinery_project.id}/create-embedding",
        json={
            "attribute_id": str(att.id),
            "config": json.dumps(
                {
                    "platform": "huggingface",
                    "termsText": None,
                    "termsAccepted": False,
                    "embeddingType": "ON_ATTRIBUTE",
                    "filterAttributes": [],
                    "model": "distilbert-base-uncased",
                }
            ),
        },
    )

    assert response.status_code == 200

    for _ in range(10):
        time.sleep(1)
        all = embedding_bo.get_all_by_attribute_ids(refinery_project.id, [str(att.id)])
        if len(all) > 0:
            break
    assert len(all) > 0
    assert all[0].type == enums.EmbeddingType.ON_ATTRIBUTE.value

    for _ in range(20):
        time.sleep(1)
        count = embedding_bo.get_tensor_count(all[0].id)
        if count > 0:
            break
    assert count > 0


def test_update_records_to_project(
    client: TestClient, refinery_project: RefineryProject, user: User
):

    upload_task = upload_task_manager.create_upload_task(
        str(user.id),
        str(refinery_project.id),
        "dummy_file_name.csv",
        "records",
        "",
        upload_type=enums.UploadTypes.DEFAULT.value,
        key=None,
    )
    record_transfer_manager.import_file_record_dict(
        refinery_project.id,
        upload_task,
        [{"running_id": 1, "data": "goodbye world"}],
    )

    assert record_bo.count(refinery_project.id) == 2
    all_records = record_bo.get_all(refinery_project.id)

    assert len(all_records) == 2
    assert any(r.data["data"] == "goodbye world" for r in all_records)
    transfer_api.__recalculate_missing_attributes_and_embeddings(
        project_id=refinery_project.id, user_id=user.id
    )
    time.sleep(5)
    emb = embedding_bo.get_all_embeddings_by_project_id(refinery_project.id)
    assert len(emb) > 0
    assert emb[0].current_delta_record_count > 0
