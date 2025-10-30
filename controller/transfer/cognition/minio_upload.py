from typing import List

from controller.transfer.cognition import etl as etl_util
from controller.task_master import manager as task_master_manager
from submodules.model.cognition_objects import (
    file_reference as file_reference_db_bo,
    markdown_file as markdown_file_bo,
    markdown_dataset as markdown_dataset_bo,
)
from submodules.model import enums
from submodules.model.business_objects import general


def handle_cognition_file_upload(path_parts: List[str]):

    if path_parts[1] != "_cognition" or len(path_parts) < 5:
        return
    if path_parts[2] == "files" and path_parts[4].startswith("file_original"):
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
                "File reference duplication error, file is already processed",
                flush=True,
            )
            if file_reference:
                print(f"File reference id: {str(file_reference.id)}", flush=True)
                print(f"File name: {file_reference.original_file_name}", flush=True)
            return
        file_reference.state = enums.FileCachingState.COMPLETED.value
        general.commit()

        priority = -1
        if (
            file_reference.meta_data.get("transformation_initiator")
            == enums.FileCachingInitiator.TMP_DOC_RETRIEVAL.value
        ):
            priority = 1
        # task_master_manager.queue_task(
        #     str(file_reference.organization_id),
        #     str(file_reference.created_by),
        #     TaskType.PARSE_COGNITION_FILE,
        #     {
        #         "parse_scope": FileCachingProcessingScope.EXTRACT_TRANSFORM.value,
        #         "file_reference_id": str(file_reference.id),
        #         "extraction_method": extraction_method,
        #         "meta_data": file_reference.meta_data,
        #         "extraction_key": file_reference.meta_data.get("extraction_key"),
        #         "transformation_key": file_reference.meta_data.get(
        #             "transformation_key"
        #         ),
        #         "file_name": file_reference.original_file_name,
        #     },
        #     prio,  # not sure if prio is right here as the prio tasks should only take < 1 min but waiting for the normal queue will take ages depending on the queue
        # )

        markdown_file = markdown_file_bo.get(
            org_id, file_reference.meta_data.get("markdown_file_id")
        )
        if not markdown_file:
            print(
                "ERROR: Markdown file not found for the given markdown_file_id",
                flush=True,
            )
            raise ValueError(
                f"Markdown file not found for file reference {file_reference.id}"
            )

        markdown_dataset = markdown_dataset_bo.get(
            org_id=org_id, id=markdown_file.dataset_id
        )
        file_type = enums.ETLFileType.from_string(markdown_file.category_origin)
        etl_task = etl_util.get_or_create_task(
            markdown_file=markdown_file,
            markdown_dataset=markdown_dataset,
            minio_path=file_reference.minio_path,
            original_file_name=file_reference.original_file_name,
            file_size_bytes=file_reference.file_size_bytes,
            file_type=file_type,
            extractor=enums.ETLExtractorPDF.from_string(
                markdown_file.meta_data.get("extractor")
            ),
            split_strategy=markdown_file.meta_data.get("split_strategy"),
            chunk_size=markdown_file.meta_data.get("chunk_size"),
            priority=priority,
        )

        task_master_manager.queue_task(
            org_id,
            str(file_reference.created_by),
            enums.TaskType.EXECUTE_ETL,
            {"etl_task_id": str(etl_task.id)},
        )
