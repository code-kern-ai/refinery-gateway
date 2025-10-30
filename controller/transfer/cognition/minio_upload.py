from typing import List

from controller.task_master import manager as task_master_manager
from submodules.model import enums
from submodules.model.business_objects import general
from submodules.model.global_objects import etl_task as etl_task_bo
from submodules.model.cognition_objects import (
    file_reference as file_reference_db_bo,
    markdown_file as markdown_file_bo,
    markdown_dataset as markdown_dataset_bo,
)


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

        chunk_size = 1000
        priority = -1
        if (
            file_reference.meta_data.get("transformation_initiator")
            == enums.FileCachingInitiator.TMP_DOC_RETRIEVAL.value
        ):
            priority = 1

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

        etl_task = etl_task_bo.get_or_create_markdown_file_etl_task(
            org_id=org_id,
            file_reference=file_reference,
            markdown_file=markdown_file,
            markdown_dataset=markdown_dataset,
            extractor=markdown_file.meta_data.get("extractor"),
            fallback_extractors=[
                enums.ETLExtractorPDF.PDF2MD,
                enums.ETLExtractorPDF.VISION,
            ],
            cache_config={
                "use_file_cache": True,
                "use_extraction_cache": False,
                "use_transformation_cache": True,
            },
            split_config={
                "strategy": enums.ETLSplitStrategy.CHUNK.value,
                "chunk_size": chunk_size,
            },
            transform_config={
                "transformers": [
                    {  # NOTE: __call_gpt_with_key only reads user_prompt
                        "enabled": True,
                        "name": enums.ETLTransformer.CLEANSE.value,
                        "system_prompt": None,
                        "user_prompt": None,
                    },
                    {
                        "enabled": True,
                        "name": enums.ETLTransformer.TEXT_TO_TABLE.value,
                        "system_prompt": None,
                        "user_prompt": None,
                    },
                    {
                        "enabled": False,
                        "name": enums.ETLTransformer.SUMMARIZE.value,
                        "system_prompt": None,
                        "user_prompt": None,
                    },
                ]
            },
            load_config={
                "refinery_project": {"enabled": False, "id": None},
                "markdown_file": {"enabled": True, "id": str(markdown_file.id)},
            },
            notify_config={
                "http": {
                    "url": "http://cognition-gateway:80/etl/finished/{markdown_file_id}",
                    "format": {
                        "markdown_file_id": str(markdown_file.id),
                    },
                    "method": "POST",
                }
            },
            priority=priority,
        )

        markdown_file_bo.update(
            org_id=org_id, markdown_file_id=markdown_file.id, etl_task_id=etl_task.id
        )

        task_master_manager.queue_task(
            org_id,
            str(file_reference.created_by),
            enums.TaskType.EXECUTE_ETL,
            {"etl_task_id": str(etl_task.id)},
        )
