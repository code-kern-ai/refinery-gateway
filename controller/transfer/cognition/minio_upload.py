from typing import List

from controller.task_master import manager as task_master_manager
from submodules.model import enums, etl_utils
from submodules.model.business_objects import general
from submodules.model.global_objects import etl_task as etl_task_bo
from submodules.model.cognition_objects import (
    file_reference as file_reference_db_bo,
    markdown_file as markdown_file_bo,
    markdown_dataset as markdown_dataset_bo,
)


def handle_cognition_file_upload(path_parts: List[str]):
    # raise NotImplementedError("This function is not yet implemented.")
    if path_parts[1] != "_cognition" or len(path_parts) < 5:
        return
    ##tmp doc retrieval => need to understand how .info file is an indicator for cognition gateway to pick it up
    if not (path_parts[2] == "files" and path_parts[4].startswith("file_original")):
        return

    org_id = path_parts[0]
    file_hash, file_size = path_parts[3].split("_")
    file_reference = file_reference_db_bo.get(org_id, file_hash, int(file_size))

    if (
        not file_reference
        or file_reference.state == enums.FileCachingState.RUNNING.value
        or file_reference.state == enums.FileCachingState.COMPLETED.value
    ):
        # file_reference is None or already processed in queue
        print(
            f"WARNING:  {__name__} - file reference duplication error, file is already processed",
            flush=True,
        )
        if file_reference:
            print(
                f"INFO:     {__name__} - file reference id: {str(file_reference.id)}",
                flush=True,
            )
            print(
                f"INFO:     {__name__} - file name: {file_reference.original_file_name}",
                flush=True,
            )
        return

    file_reference.state = enums.FileCachingState.COMPLETED.value
    general.commit()

    if (
        file_reference.meta_data.get("file_caching_initiator")
        == enums.FileCachingInitiator.TMP_DOC_RETRIEVAL.value
    ):
        project_id = file_reference.meta_data.get("project_id")
        conversation_id = file_reference.meta_data.get("conversation_id")
        full_config, tokenizer = etl_utils.get_full_config_and_tokenizer_from_config_id(
            file_reference, project_id=project_id, conversation_id=conversation_id
        )
        etl_task = etl_task_bo.create(
            org_id,
            file_reference.created_by,
            file_reference.original_file_name,
            file_reference.file_size_bytes,
            full_config=full_config,
            tokenizer=tokenizer,
            priority=1,
        )

        task_master_manager.queue_task(
            org_id,
            str(file_reference.created_by),
            enums.TaskType.EXECUTE_ETL,
            {
                "etl_task_id": str(etl_task.id),
                "file_reference_id": str(file_reference.id),
                "tmp_doc_metadata": {
                    "project_id": project_id,
                    "conversation_id": conversation_id,
                },
            },
            priority=True,
        )

    else:
        priority = -1

        markdown_dataset = markdown_dataset_bo.get(
            org_id, file_reference.meta_data.get("dataset_id")
        )

        markdown_file = markdown_file_bo.get(
            org_id, file_reference.meta_data.get("markdown_file_id")
        )

        etl_task = etl_task_bo.create(
            org_id,
            file_reference.created_by,
            file_reference.original_file_name,
            file_reference.file_size_bytes,
            full_config=etl_utils.get_full_config_for_markdown_file(
                file_reference,
                markdown_dataset,
                markdown_file,
            ),
            tokenizer=markdown_dataset.tokenizer,
            priority=priority,
        )

        markdown_file_bo.update(
            org_id=org_id,
            markdown_file_id=markdown_file.id,
            etl_task_id=etl_task.id,
        )

        task_master_manager.queue_task(
            org_id,
            str(file_reference.created_by),
            enums.TaskType.EXECUTE_ETL,
            {
                "etl_task_id": str(etl_task.id),
                "file_reference_id": str(file_reference.id),
            },
            priority=priority != -1,
        )
