from fastapi import APIRouter, Body, Depends, Request
from controller.knowledge_base import manager as base_manager
from controller.knowledge_term import manager as terms_manager
from controller.transfer import manager as transfer_manager
from fast_api.models import AddTermToKnowledgeBaseBody, UpdateKnowledgeBaseBody
from submodules.model.util import sql_alchemy_to_dict
from controller.auth import manager as auth_manager
from util import notification as prj_notification
from controller.auth.manager import get_user_by_info

router = APIRouter()

LOOKUP_LIST_WHITELIST = ["id", "name", "description"]

LOOKUP_LIST_TERM_WHITELIST = [
    "id",
    "value",
    "comment",
    "blacklisted",
]


@router.get("/{project_id}/get-lookup-lists-by-project-id")
def get_lookup_lists_by_project_id(
    project_id: str, access: bool = Depends(auth_manager.check_project_access_dep)
):
    data = base_manager.get_all_knowledge_bases(project_id)
    term_data = []
    for lookup_list in data:
        terms = terms_manager.get_terms_by_knowledge_base(project_id, lookup_list.id)
        term_data.append(
            {
                "id": lookup_list.id,
                "name": lookup_list.name,
                "description": lookup_list.description,
                "termCount": len(terms),
            }
        )

    return {"data": {"knowledgeBasesByProjectId": term_data}}


@router.get(
    "/{project_id}/{lookup_list_id}/get-lookup-lists-by-lookup-list-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_lookup_lists_by_lookup_list_id(
    project_id: str,
    lookup_list_id: str,
):
    data = base_manager.get_knowledge_base(project_id, lookup_list_id)
    data_dict = sql_alchemy_to_dict(data, column_whitelist=LOOKUP_LIST_WHITELIST)
    return {"data": {"knowledgeBaseByKnowledgeBaseId": data_dict}}


@router.get(
    "/{project_id}/{lookup_list_id}/terms",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_terms_by_lookup_list_id(
    project_id: str,
    lookup_list_id: str,
):
    data = terms_manager.get_terms_by_knowledge_base(project_id, lookup_list_id)
    data_dict = sql_alchemy_to_dict(data, column_whitelist=LOOKUP_LIST_TERM_WHITELIST)
    return {"data": {"termsByKnowledgeBaseId": data_dict}}


@router.get(
    "/{project_id}/{lookup_list_id}/export",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_export_lookup_list(
    project_id: str,
    lookup_list_id: str,
):
    return {
        "data": {
            "exportKnowledgeBase": transfer_manager.export_knowledge_base(
                project_id, lookup_list_id
            )
        }
    }


@router.post(
    "/{project_id}/create-knowledge-base",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_knowledge_base(
    project_id: str,
):
    knowledge_base = base_manager.create_knowledge_base(project_id)

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


@router.delete(
    "/{project_id}/delete-knowledge-base/{knowledge_base_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_knowledge_base(
    project_id: str,
    knowledge_base_id: str,
):
    base_manager.delete_knowledge_base(project_id, knowledge_base_id)

    prj_notification.send_organization_update(
        project_id, f"knowledge_base_deleted:{str(knowledge_base_id)}"
    )

    return {"data": {"deleteKnowledgeBase": {"ok": True}}}


@router.put(
    "/{project_id}/update-knowledge-base",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_knowledge_base(
    project_id: str,
    request: Request,
    updateKnowledgeBaseBody: UpdateKnowledgeBaseBody = Body(...),
):
    user = get_user_by_info(request.state.info)

    base_manager.update_knowledge_base(
        project_id,
        user.id,
        updateKnowledgeBaseBody.knowledge_base_id,
        updateKnowledgeBaseBody.name,
        updateKnowledgeBaseBody.description,
    )

    prj_notification.send_organization_update(
        str(project_id),
        f"knowledge_base_updated:{str(updateKnowledgeBaseBody.knowledge_base_id)}",
    )

    return {"data": {"updateKnowledgeBase": {"ok": True}}}


@router.post("/{project_id}/add-term-to-knowledge-base")
def add_term_to_knowledge_base(
    project_id: str,
    request: Request,
    termBody: AddTermToKnowledgeBaseBody = Body(...),
):
    user = get_user_by_info(request.state.info)

    terms_manager.create_term(
        user.id,
        project_id,
        termBody.knowledge_base_id,
        termBody.value,
        termBody.comment,
    )

    prj_notification.send_organization_update(
        str(project_id),
        f"knowledge_base_term_updated:{str(termBody.knowledge_base_id)}",
    )

    return {"data": {"addTermToKnowledgeBase": {"ok": True}}}


@router.delete("/{project_id}/delete-term/{term_id}")
def delete_term(
    project_id: str,
    term_id: str,
):
    base = base_manager.get_knowledge_base_by_term(project_id, term_id)
    terms_manager.delete_term(project_id, term_id)

    prj_notification.send_organization_update(
        project_id, f"knowledge_base_term_updated:{str(base.id)}"
    )

    return {"data": {"deleteTerm": {"ok": True}}}
