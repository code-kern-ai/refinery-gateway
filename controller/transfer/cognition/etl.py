from typing import Optional

from submodules.model import enums
from submodules.model.models import (
    EtlTask,
    CognitionMarkdownFile,
    CognitionMarkdownDataset,
)
from submodules.model.global_objects import etl_task as etl_task_bo
from submodules.model.cognition_objects import markdown_file as markdown_file_bo

DEFAULT_FILE_TYPE = enums.ETLFileType.PDF
DEFAULT_EXTRACTORS = {
    enums.ETLFileType.MD: enums.ETLExtractor.MD.FILESYSTEM,
    enums.ETLFileType.PDF: enums.ETLExtractor.PDF.PDF2MD,
}

DEFAULT_FALLBACK_EXTRACTORS = {
    enums.ETLFileType.PDF: [
        enums.ETLExtractor.PDF.PDF2MD,
        enums.ETLExtractor.PDF.VISION,
        enums.ETLExtractor.PDF.AZURE_DI,
    ],
}


def get_or_create_task(
    markdown_file: CognitionMarkdownFile,
    markdown_dataset: CognitionMarkdownDataset,
    file_size_bytes: int,
    minio_path: str,
    original_file_name: str,
    file_type: Optional[enums.ETLFileType] = None,
    extractor: Optional[enums.ETLExtractor] = None,
    fallback_extractors: Optional[list[enums.ETLExtractor]] = None,
    split_strategy: Optional[enums.ETLSplitStrategy] = None,
    chunk_size: Optional[int] = 1000,
    priority: Optional[int] = -1,
) -> EtlTask:
    if markdown_file.etl_task_id:
        if etl_task := etl_task_bo.get_by_id(markdown_file.etl_task_id):
            return etl_task

    file_type = file_type or DEFAULT_FILE_TYPE
    split_strategy = split_strategy or enums.ETLSplitStrategy.CHUNK
    extractor = extractor or DEFAULT_EXTRACTORS[file_type]
    fallback_extractors = list(
        filter(
            lambda x: x != extractor,
            (fallback_extractors or DEFAULT_FALLBACK_EXTRACTORS.get(file_type, [])),
        )
    )

    etl_task = etl_task_bo.create(
        org_id=markdown_dataset.organization_id,
        user_id=markdown_file.created_by,
        file_size_bytes=file_size_bytes,
        extract_config={
            "file_type": file_type.value,
            "extractor": extractor.value,
            "fallback_extractors": [fe.value for fe in fallback_extractors],
            "minio_path": minio_path,
            "original_file_name": original_file_name,
        },
        split_config={
            "strategy": split_strategy.value,
            "chunk_size": chunk_size,
        },
        transform_config={
            "transformers": [
                {
                    "name": enums.ETLTransformer.CLEANSE.value,
                    "system_prompt": None,
                    "user_prompt": None,
                },
                {
                    "name": enums.ETLTransformer.TEXT_TO_TABLE.value,
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
        llm_config=markdown_dataset.llm_config,
        tokenizer=markdown_dataset.tokenizer,
        priority=priority,
    )

    markdown_file_bo.update(
        org_id=markdown_file.organization_id,
        markdown_file_id=markdown_file.id,
        etl_task_id=etl_task.id,
    )

    return etl_task
