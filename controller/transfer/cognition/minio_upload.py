from typing import List
from submodules.model.cognition_objects import file_reference as file_reference_db_bo
from submodules.model.enums import TaskType, FileCacheProcessingScope
from controller.task_master import manager as task_master_manager
from submodules.model import enums


def handle_cognition_file_upload(path_parts: List[str]):

    if path_parts[1] != "_cognition":
        return
    if path_parts[2] == "files" and path_parts[4] == "queued":
        org_id = path_parts[0]
        file_hash, file_size = path_parts[3].split("_")
        file_reference = file_reference_db_bo.get(org_id, file_hash, int(file_size))

        if not file_reference:
            return

        prio = (
            file_reference.meta_data.get("transformation_initiator")
            == enums.MarkdownTransformationInitiator.TMP_DOC_RETRIEVAL.value
        )

        extraction_method = file_reference.meta_data.get("extraction_method")

        task_master_manager.queue_task(
            str(file_reference.organization_id),
            str(file_reference.created_by),
            TaskType.PARSE_COGNITION_FILE,
            {
                "parse_scope": FileCacheProcessingScope.EXTRACT_TRANSFORM.value,
                "file_reference_id": str(file_reference.id),
                "extraction_method": extraction_method,
                "meta_data": file_reference.meta_data,
            },
            prio,  # not sure if prio is right here as the prio tasks should only take < 1 min but waiting for the normal queue will take ages depending on the queue
        )
