from typing import List, Dict, Any, Optional
from controller.auth import kratos, manager as auth_manager
from fast_api.models import (
    InboxMailCreateRequest,
    UpdateInboxMailThreadProgressRequest,
)
from controller.inbox_mail import manager as inbox_mail_manager
from submodules.model.global_objects import inbox_mail as inbox_mail_go
from fastapi import APIRouter, HTTPException, Request, Query
from fast_api.routes.client_response import (
    get_silent_success,
    pack_json_result,
)

router = APIRouter()


@router.post("")
def create_inbox_mail_by_thread(request: Request, inbox_mail: InboxMailCreateRequest):
    user_is_admin = auth_manager.check_admin_access(request.state)
    user = auth_manager.get_user_by_info(request.state.info)

    if inbox_mail.threadId:
        inbox_mail_thread = inbox_mail_go.get_inbox_mail_thread_by_id(
            thread_id=inbox_mail.threadId,
        )
        if not inbox_mail_thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        if not user_is_admin and (
            (str(inbox_mail_thread.organization_id) != str(user.organization_id))
            or not inbox_mail_go.get_inbox_mail_thread_association_by_thread_id_and_user_id(
                thread_id=inbox_mail.threadId,
                user_id=str(user.id),
            )
        ):
            raise HTTPException(status_code=403, detail="Not authorized")

    mail = inbox_mail_manager.create_inbox_mail_by_thread(
        org_id=user.organization_id,
        sender_id=str(user.id),
        recipient_ids=inbox_mail.recipientIds,
        subject=inbox_mail.subject,
        content=inbox_mail.content,
        meta_data=inbox_mail.metaData,
        thread_id=inbox_mail.threadId,
        is_important=inbox_mail.isImportant,
        is_admin_support_thread=inbox_mail.isAdminSupportThread,
    )
    return pack_json_result(mail)


@router.get("/thread/{thread_id}")
def get_inbox_mails_by_thread(request: Request, thread_id: str) -> List[Dict[str, Any]]:
    user_is_admin = auth_manager.check_admin_access(request.state)

    user = auth_manager.get_user_by_info(request.state.info)

    mails = inbox_mail_manager.get_inbox_mails_by_thread(
        org_id=user.organization_id,
        user_id=str(user.id),
        user_is_admin=user_is_admin,
        thread_id=thread_id,
    )
    return pack_json_result(mails)


@router.get("/overview")
def get_inbox_mail_thread_overview_paginated(
    request: Request,
    page: int = 1,
    limit: int = 10,
    filters: Optional[List[str]] = Query(default=None),
):
    user_is_admin = auth_manager.check_admin_access(request.state)
    user = auth_manager.get_user_by_info(request.state.info)
    mail = inbox_mail_manager.get_inbox_mail_threads_overview(
        org_id=user.organization_id,
        user_id=str(user.id),
        page=page,
        limit=limit,
        user_is_admin=user_is_admin,
        filters=filters,
    )
    return pack_json_result(mail)


@router.put("/thread/{thread_id}/progress")
def update_inbox_mail_thread_progress(
    request: Request,
    thread_id: str,
    inbox_mail_thread_update: UpdateInboxMailThreadProgressRequest,
):
    user_is_admin = auth_manager.check_admin_access(request.state)
    user = auth_manager.get_user_by_info(request.state.info)

    inbox_mail_thread = inbox_mail_go.get_inbox_mail_thread_by_id(thread_id=thread_id)
    if not inbox_mail_thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if not user_is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    user_name = kratos.resolve_user_name_by_id(str(user.id))
    inbox_mail_go.update_thread_progress(
        str(user.id),
        thread_id=thread_id,
        progress_state=inbox_mail_thread_update.progressState,
        user_name=user_name,
        with_commit=True,
    )
    return get_silent_success()


@router.delete("/{mail_id}")
def delete_inbox_mail_by_id(request: Request, mail_id: str):
    inbox_mail_entity = inbox_mail_go.get(inbox_mail_id=mail_id)
    user = auth_manager.get_user_by_info(request.state.info)
    if not inbox_mail_entity:
        raise HTTPException(status_code=404, detail="Mail not found")

    if str(inbox_mail_entity.sender_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    thread_id = inbox_mail_entity.thread_id
    inbox_mail_go.delete(inbox_mail_id=mail_id, with_commit=True)
    # If no mails are left in the thread, delete the thread as well
    remaining_mails = inbox_mail_go.get_inbox_mail_thread_length(thread_id=thread_id)
    if remaining_mails == 0:
        inbox_mail_go.delete_thread_by_id(thread_id)
    return get_silent_success()


@router.get("/new")
def has_new_inbox_mails(request: Request):
    user_is_admin = auth_manager.check_admin_access(request.state)
    user = auth_manager.get_user_by_info(request.state.info)

    total_new_inbox_mails = inbox_mail_manager.get_new_inbox_mails_info(
        org_id=user.organization_id,
        user_id=user.id,
        user_is_admin=user_is_admin,
    )
    return pack_json_result(
        {
            "totalNewInboxMails": total_new_inbox_mails,
        }
    )


@router.put("/thread/{thread_id}/unread/project")
def update_inbox_mail_threads_unread_by_project(request: Request, thread_id: str):
    user_is_admin = auth_manager.check_admin_access(request.state)
    if not user_is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    inbox_mail_thread = inbox_mail_go.get_inbox_mail_thread_by_id(thread_id=thread_id)
    if not inbox_mail_thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    inbox_mail_go.update_system_support_threads_read_by_threads_project(
        thread_id=thread_id
    )
    return get_silent_success()


@router.put("/thread/{thread_id}/unread/content")
def update_inbox_mail_threads_unread_by_content(request: Request, thread_id: str):
    user_is_admin = auth_manager.check_admin_access(request.state)
    if not user_is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    inbox_mail_thread = inbox_mail_go.get_inbox_mail_thread_by_id(thread_id=thread_id)
    if not inbox_mail_thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    inbox_mail_go.update_system_support_threads_read_by_threads_content(
        thread_id=thread_id
    )
    return get_silent_success()


@router.put("/thread/{thread_id}/unread-last")
def mark_inbox_mail_thread_as_unread(request: Request, thread_id: str):
    user_is_admin = auth_manager.check_admin_access(request.state)
    if not user_is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    inbox_mail_thread = inbox_mail_go.get_inbox_mail_thread_by_id(thread_id=thread_id)
    if not inbox_mail_thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    inbox_mail_go.mark_thread_as_unread(thread_id=thread_id)
    return get_silent_success()


@router.delete("/thread/{thread_id}/similar")
def delete_similar_system_threads(request: Request, thread_id: str):
    user_is_admin = auth_manager.check_admin_access(request.state)
    if not user_is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    inbox_mail_thread = inbox_mail_go.get_inbox_mail_thread_by_id(thread_id=thread_id)
    if not inbox_mail_thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # only allowed for autoGenerated system threads
    meta_data = inbox_mail_thread.meta_data or {}
    if not meta_data.get("autoGenerated"):
        raise HTTPException(
            status_code=400, detail="Only allowed for auto-generated system threads"
        )

    deleted_count = inbox_mail_go.delete_system_threads_by_content(thread_id=thread_id)
    return pack_json_result({"deletedCount": deleted_count})
