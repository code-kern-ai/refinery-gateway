from typing import List, Tuple

from submodules.model.business_objects import (
    information_source as refinery_information_source,
    embedding as refinery_embedding,
)
from submodules.model.enums import PayloadState, EmbeddingState


from . import gates_service


def start_gates_container(
    project_id: str, select_available_heuristics: bool = True
) -> bool:
    heuristics, embeddings = [], []
    if select_available_heuristics:
        heuristics, embeddings = __get_relevant_gate_ids(project_id)
    return gates_service.start_gates_project(project_id, heuristics, embeddings)


def __get_relevant_gate_ids(project_id: str) -> Tuple[List[str], List[str]]:
    embeddings = [
        str(e.id)
        for e in refinery_embedding.get_all_embeddings_by_project_id(project_id)
        if e.state == EmbeddingState.FINISHED.value
    ]

    states = refinery_information_source.get_all_states(project_id)
    heuristics = [key for key in states if states[key] == PayloadState.FINISHED.value]
    return heuristics, embeddings
