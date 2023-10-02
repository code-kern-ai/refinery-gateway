from typing import List, Tuple

from submodules.model.cognition_objects import (
    project as cognition_project,
)
from submodules.model.business_objects import (
    information_source as refinery_information_source,
    embedding as refinery_embedding,
    general,
)
from submodules.model.enums import PayloadState, EmbeddingState

from util import notification, daemon

from . import gates_service


def start_gates_for_cognition_project(cognition_project_id: str) -> None:
    cognition_project_item = cognition_project.get(cognition_project_id)
    if not cognition_project_item:
        # was deleted in the meantime -> nothing to do
        return

    # unbind through cast to prevent session timeout issues
    refinery_relevance_id = str(cognition_project_item.refinery_relevance_project_id)
    refinery_query_id = str(cognition_project_item.refinery_query_project_id)
    refinery_reference_id = str(cognition_project_item.refinery_references_project_id)
    organization_id = str(cognition_project_item.organization_id)

    daemon.run(
        __prepare_gates_and_finish,
        cognition_project_id,
        refinery_reference_id,
        refinery_query_id,
        refinery_relevance_id,
        organization_id,
    )


def __prepare_gates_and_finish(
    cognition_project_id: str,
    refinery_reference_id: str,
    refinery_query_id: str,
    refinery_relevance_id: str,
    organization_id: str,
) -> None:
    notification.send_organization_update(
        cognition_project_id,
        "cognition_prep:state:SETUP_GATES",
        organization_id=organization_id,
    )
    notification.send_organization_update(
        cognition_project_id,
        "cognition_prep:progress:0",
        organization_id=organization_id,
    )
    heuristics, embeddings = __get_relevant_gate_ids(refinery_reference_id)
    gates_service.start_gates_project(refinery_reference_id, heuristics, embeddings)
    notification.send_organization_update(
        cognition_project_id,
        "cognition_prep:progress:33",
        organization_id=organization_id,
    )
    heuristics, embeddings = __get_relevant_gate_ids(refinery_query_id)
    gates_service.start_gates_project(refinery_query_id, heuristics, embeddings)
    notification.send_organization_update(
        cognition_project_id,
        "cognition_prep:progress:66",
        organization_id=organization_id,
    )
    heuristics, embeddings = __get_relevant_gate_ids(refinery_relevance_id)
    gates_service.start_gates_project(refinery_relevance_id, heuristics, embeddings)

    notification.send_organization_update(
        cognition_project_id,
        f"cognition_prep:state:DONE",
        organization_id=organization_id,
    )
    ctx_token = general.get_ctx_token()
    cognition_project_item = cognition_project.get(cognition_project_id)
    cognition_project_item.wizard_running = False
    general.commit()
    general.remove_and_refresh_session(ctx_token, False)


def __get_relevant_gate_ids(project_id: str) -> Tuple[List[str], List[str]]:
    embeddings = [
        str(e.id)
        for e in refinery_embedding.get_all_embeddings_by_project_id(project_id)
        if e.state == EmbeddingState.FINISHED.value
    ]

    states = refinery_information_source.get_all_states(project_id)
    heuristics = [key for key in states if states[key] == PayloadState.FINISHED.value]
    return heuristics, embeddings
