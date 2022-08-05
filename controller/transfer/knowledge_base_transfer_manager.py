import os
from submodules.model import UploadTask, enums
from submodules.model.business_objects import knowledge_term, organization
from submodules.model.business_objects import general
from controller.upload_task import manager as task_manager
from submodules.s3 import controller as s3
import pandas as pd


def import_knowledge_base_file(project_id: str, task: UploadTask) -> None:
    task_manager.update_task(
        project_id, task.id, state=enums.UploadStates.PENDING.value
    )
    general.commit()

    file_type = task.file_name.rsplit("_", 1)[0].rsplit(".", 1)[1]
    list_id = task.file_name.rsplit("_", 1)[1]

    existing_items = knowledge_term.get_by_knowledge_base(list_id)
    existing_names = {str(row.value) for row in existing_items}
    org_id = organization.get_id_by_project_id(project_id)

    download_file_name = s3.download_object(
        org_id, project_id + "/" + f"{task.id}/{task.file_name}", file_type
    )
    if file_type in ["csv", "txt", "text"]:
        df = pd.read_csv(download_file_name)
    elif file_type == "xlsx":
        df = pd.read_excel(download_file_name)
    elif file_type == "html":
        df = pd.read_html(download_file_name)
    elif file_type == "json":
        df = pd.read_json(download_file_name)

    if os.path.exists(download_file_name):
        os.remove(download_file_name)

    try:
        import_exported_file(project_id, list_id, df)
    except Exception:
        general.rollback()
        term_list = set(df["value"].unique())
        to_add = term_list - existing_names
        knowledge_term.create_by_value_list(
            project_id, list_id, to_add, with_commit=True
        )

    task_manager.update_task(
        project_id, task.id, state=enums.UploadStates.IN_PROGRESS.value
    )
    task.state = enums.UploadStates.DONE.value
    general.commit()


def import_exported_file(
    project_id: str, knowledge_base_id: str, df: pd.DataFrame
) -> None:
    """
    try to import the structure of export
    if the structure does not fit an exception gets raised
    and the original import flow is done
    """
    for value in df["terms"]:
        term = knowledge_term.get_by_value(knowledge_base_id, value.get("value"))
        if term:
            term.comment = value["comment"]
            term.blacklisted = value["blacklisted"]
        else:
            knowledge_term.create(
                project_id,
                knowledge_base_id,
                value["value"],
                value["comment"],
                value["blacklisted"],
            )
