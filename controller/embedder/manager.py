from typing import List
from submodules.model import Embedder
from submodules.model.business_objects import embedder


def get_embedder(project_id: str, embedder_id: str) -> Embedder:
    return embedder.get(project_id, embedder_id)


def get_all_embedders(project_id: str) -> List[Embedder]:
    return embedder.get_all(project_id)


def get_overview_data(project_id: str) -> str:
    return embedder.get_overview_data(project_id)


def create_embedder(
    project_id: str,
    user_id: str,
    name: str,
    source_code: str,
    description: str,
    type: str,
) -> Embedder:
    embedder: Embedder = embedder.create(
        project_id=project_id,
        name=name,
        source_code=source_code,
        description=description,
        type=type,
        created_by=user_id,
        with_commit=True,
    )
    return embedder


def update_embedder(
    project_id: str,
    embedder_id: str,
    code: str,
    description: str,
    name: str,
) -> None:
    embedder.update(
        project_id,
        embedder_id,
        source_code=code,
        description=description,
        name=name,
        with_commit=True,
    )


def delete_embedder(project_id: str, embedder_id: str) -> None:
    embedder.delete(project_id, embedder_id, with_commit=True)
