from fastapi import APIRouter, Request
from controller.knowledge_base import manager
from controller.knowledge_term import manager as manager_terms

router = APIRouter()


@router.get("/lookup-lists/{project_id}")
def get_lookup_lists(project_id: str):

    data = manager.get_all_knowledge_bases(project_id)
    term_data = []
    for lookup_list in data:
        terms = manager_terms.get_terms_by_knowledge_base(project_id, lookup_list.id)
        term_data.append(
            {
                "id": lookup_list.id,
                "name": lookup_list.name,
                "description": lookup_list.description,
                "termCount": len(terms),
            }
        )

    return {"data": {"knowledgeBasesByProjectId": term_data}}


@router.get("/lookup-lists/{project_id}/{lookup_list_id}")
def get_lookup_lists_by_lookup_list_id(project_id: str, lookup_list_id: str):
    data = manager.get_knowledge_base(project_id, lookup_list_id)
    return {"data": {"knowledgeBaseByKnowledgeBaseId": data}}


@router.get("/lookup-lists/{project_id}/{lookup_list_id}/terms")
def get_terms_by_lookup_list_id(project_id: str, lookup_list_id: str):
    data = manager_terms.get_terms_by_knowledge_base(project_id, lookup_list_id)
    return {"data": {"termsByKnowledgeBaseId": data}}
