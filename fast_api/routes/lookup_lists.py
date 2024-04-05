from fastapi import APIRouter, Depends
from controller.knowledge_base import manager
from controller.knowledge_term import manager as manager_terms
from controller.transfer import manager as transfer_manager
from submodules.model.util import sql_alchemy_to_dict
from controller.auth import manager as auth_manager
from util import notification as prj_notification

router = APIRouter()

LOOKUP_LIST_WHITELIST = ["id", "name", "description"]

LOOKUP_LIST_TERM_WHITELIST = [
    "id",
    "value",
    "comment",
    "blacklisted",
]


@router.get("/lookup-lists/{project_id}")
def get_lookup_lists(
    project_id: str, access: bool = Depends(auth_manager.check_project_access_dep)
):

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


@router.get("/{project_id}/{lookup_list_id}/get-lookup-list-by-lookup-list-id")
def get_lookup_lists_by_lookup_list_id(
    project_id: str,
    lookup_list_id: str,
    access: bool = Depends(auth_manager.check_project_access_dep),
):
    data = manager.get_knowledge_base(project_id, lookup_list_id)
    data_dict = sql_alchemy_to_dict(data, column_whitelist=LOOKUP_LIST_WHITELIST)
    return {"data": {"knowledgeBaseByKnowledgeBaseId": data_dict}}


@router.get("/{project_id}/{lookup_list_id}/terms")
def get_terms_by_lookup_list_id(
    project_id: str,
    lookup_list_id: str,
    access: bool = Depends(auth_manager.check_project_access_dep),
):
    data = manager_terms.get_terms_by_knowledge_base(project_id, lookup_list_id)
    data_dict = sql_alchemy_to_dict(data, column_whitelist=LOOKUP_LIST_TERM_WHITELIST)
    return {"data": {"termsByKnowledgeBaseId": data_dict}}


@router.get("/{project_id}/{lookup_list_id}/export")
def get_export_lookup_list(
    project_id: str,
    lookup_list_id: str,
    access: bool = Depends(auth_manager.check_project_access_dep),
):
    return {
        "data": {
            "exportKnowledgeBase": transfer_manager.export_knowledge_base(
                project_id, lookup_list_id
            )
        }
    }


@router.post("/{project_id}/knowledge-base")
def create_knowledge_base(
    project_id: str,
    access: bool = Depends(auth_manager.check_project_access_dep),
):
    knowledge_base = manager.create_knowledge_base(project_id)

    prj_notification.send_organization_update(
        project_id, f"knowledge_base_created:{str(knowledge_base.id)}"
    )

    data = {
        "knowledgeBase": {
            "id": str(knowledge_base.id),
            "name": knowledge_base.name,
            "description": knowledge_base.description,
            "termCount": len(knowledge_base.terms),
        }
    }

    return {"data": {"createKnowledgeBase": data}}
