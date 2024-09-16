from typing import Any, List, Dict
from submodules.model.business_objects import monitor as task_monitor
from controller.auth import kratos
from submodules.model.util import sql_alchemy_to_dict


def monitor_all_tasks(page: int, limit: int) -> List[Any]:
    tasks = task_monitor.get_all_tasks(page, limit)
    tasks_dict = sql_alchemy_to_dict(tasks)
    user_ids = {str(t["created_by"]) for t in tasks}  # set comprehension
    name_lookup = {u_id: kratos.resolve_user_name_by_id(u_id) for u_id in user_ids}

    for t in tasks_dict:
        created_by_first_last = name_lookup[str(t["created_by"])]
        t["created_by"] = (
            created_by_first_last["first"] + " " + created_by_first_last["last"]
            if created_by_first_last
            else "Unknown"
        )

        # name comes from the join with organization
        t["organization_name"] = t["name"]
        del t["name"]

    return tasks_dict


def cancel_all_running_tasks(project_id: str = None) -> None:
    task_monitor.cancel_all_running_tasks(project_id)


def cancel_upload_task(project_id: str = None, upload_task_id: str = None) -> None:
    task_monitor.set_upload_task_to_failed(project_id, upload_task_id, with_commit=True)


def cancel_weak_supervision(
    task_info: Dict[str, Any],
) -> None:
    project_id = task_info.get("project_id")
    payload_id = task_info.get("payload_id")
    task_monitor.set_weak_supervision_to_failed(
        project_id, payload_id, with_commit=True
    )


def cancel_attribute_calculation(
    task_info: Dict[str, Any],
) -> None:

    project_id = task_info.get("project_id")
    attribute_id = task_info.get("attribute_id")
    task_monitor.set_attribute_calculation_to_failed(
        project_id, attribute_id, with_commit=True
    )


def cancel_embedding(
    task_info: Dict[str, Any],
) -> None:
    project_id = task_info.get("project_id")
    embedding_id = task_info.get("embedding_id")

    task_monitor.set_embedding_to_failed(project_id, embedding_id, with_commit=True)


def cancel_information_source_payload(
    task_info: Dict[str, Any],
) -> None:
    project_id = task_info.get("project_id")
    payload_id = task_info.get("payload_id")

    task_monitor.set_information_source_payloads_to_failed(
        project_id, payload_id, with_commit=True
    )


def cancel_record_tokenization_task(
    task_info: Dict[str, Any],
) -> None:
    project_id = task_info.get("project_id")
    tokenization_task_id = task_info.get("tokenization_id")
    task_monitor.set_record_tokenization_task_to_failed(
        project_id, tokenization_task_id, with_commit=True
    )


def cancel_macro_execution_task(
    task_info: Dict[str, Any],
) -> None:
    macro_execution_id = task_info.get("macro_execution_id")
    macro_execution_group_id = task_info.get("macro_execution_group_id")
    task_monitor.set_macro_execution_task_to_failed(
        macro_execution_id, macro_execution_group_id, with_commit=True
    )


def cancel_markdown_file_task(
    task_info: Dict[str, Any],
) -> None:
    markdown_file_id = task_info.get("fileId")
    org_id = task_info.get("orgId")
    task_monitor.set_markdown_file_task_to_failed(
        markdown_file_id, org_id, with_commit=True
    )
