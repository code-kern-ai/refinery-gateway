from typing import List, Optional

from fast_api.models import CreateEmbeddingBody, UpdateEmbeddingBody
from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Body, Depends, Request
from controller.embedding import manager
from controller.task_master import manager as task_master_manager
from controller.auth import manager as auth_manager
from controller.embedding.connector import collection_on_qdrant
from submodules.model.enums import TaskType
from submodules.model.business_objects import embedding
from submodules.model.util import sql_alchemy_to_dict
from util import notification, spacy_util
import json


router = APIRouter()

ALL_EMBEDDINGS_WHITELIST = [
    "id",
    "name",
    "custom",
    "type",
    "state",
    "progress",
    "dimension",
    "count",
    "platform",
    "model",
    "filter_attributes",
    "attribute_id",
]


@router.get("/embedding-platforms")
def get_embedding_platforms():
    data = manager.get_terms_info()
    return pack_json_result(data)


@router.get("/recommended-encoders")
def data_slices(request: Request, project_id: Optional[str] = None) -> List:
    data = manager.get_recommended_encoders()
    for v in data:
        v["applicability"] = json.dumps(v["applicability"])
    return pack_json_result(data)


@router.get("/language-models")
def language_models(request: Request) -> List:
    data = spacy_util.get_language_models()
    return pack_json_result(data)


@router.get(
    "/{project_id}/embeddings-by-project",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_embeddings(project_id: str) -> List:
    embeddings_extended = embedding.get_all_embeddings_by_project_id_extended(
        project_id
    )
    data = {
        "id": project_id,
        "embeddings": [
            {
                **sql_alchemy_to_dict(
                    embedding, column_whitelist=ALL_EMBEDDINGS_WHITELIST
                ),
                "on_qdrant": collection_on_qdrant(project_id, embedding["id"]),
            }
            for embedding in embeddings_extended
        ],
    }
    return pack_json_result(data)


@router.delete(
    "/{project_id}/{task_id}/delete-from-task-queue",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_from_task_queue(
    request: Request,
    task_id: str,
):
    org_id = auth_manager.get_user_by_info(request.state.info).organization_id
    task_master_manager.delete_task(org_id, task_id)
    return pack_json_result({"ok": True})


@router.delete(
    "/{project_id}/{embedding_id}/delete-embedding",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_embedding(
    request: Request,
    project_id: str,
    embedding_id: str,
):
    manager.delete_embedding(project_id, embedding_id)
    notification.send_organization_update(
        project_id, f"embedding_deleted:{embedding_id}"
    )
    return pack_json_result({"ok": True})


@router.post(
    "/{project_id}/create-embedding",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_embedding(
    request: Request,
    project_id: str,
    body: CreateEmbeddingBody = Body(...),
):
    user = auth_manager.get_user_by_info(request.state.info)
    body.config = json.loads(body.config)
    embedding_type = body.config[
        "embeddingType"
    ]  # should raise an exception if not present
    platform = body.config.get("platform")
    model = body.config.get("model")
    api_token = body.config.get("apiToken")
    terms_text = body.config.get("termsText")
    terms_accepted = body.config.get("termsAccepted")
    filter_attributes = body.config.get("filterAttributes")

    additional_data = None
    if body.config.get("base") is not None:
        additional_data = {
            "base": body.config.get("base"),
            "type": body.config.get("type"),
            "version": body.config.get("version"),
        }

    task_master_manager.queue_task(
        str(user.organization_id),
        str(user.id),
        TaskType.EMBEDDING,
        {
            "project_id": project_id,
            "embedding_type": embedding_type,
            "attribute_id": body.attribute_id,
            "embedding_name": manager.get_embedding_name(
                project_id,
                body.attribute_id,
                platform,
                embedding_type,
                model,
                api_token,
            ),
            "platform": platform,
            "model": model,
            "api_token": api_token,
            "terms_text": terms_text,
            "terms_accepted": terms_accepted,
            "filter_attributes": filter_attributes,
            "additional_data": additional_data,
        },
    )
    notification.send_organization_update(
        project_id=project_id, message="embedding:queued"
    )
    return pack_json_result({"ok": True})


@router.post(
    "/{project_id}/update-embedding-payload",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_embedding_payload(
    project_id: str,
    updateEmbeddingBody: UpdateEmbeddingBody = Body(...),
):
    went_through = manager.update_embedding_payload(
        project_id,
        updateEmbeddingBody.embedding_id,
        updateEmbeddingBody.filter_attributes,
    )

    if went_through:
        notification.send_organization_update(
            project_id, f"embedding_updated:{updateEmbeddingBody.embedding_id}"
        )

    return pack_json_result({"ok": went_through})
