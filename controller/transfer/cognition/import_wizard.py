from typing import List, Optional

from submodules.model import UploadTask, enums
from submodules.model.business_objects import general

from controller.upload_task import manager as upload_task_manager
from controller.labeling_task import manager as labeling_task_manager
from controller.labeling_task_label import manager as label_manager
from controller.attribute import manager as attribute_manager
from .wizard_function_templates import LANGUAGE_DETECTION, REFERENCE_CHUNKS


def finalize_reference_setup(
    cognition_project_id: str, project_id: str, task_id: str
) -> None:
    # task = upload_task_manager.get_upload_task(
    #     task_id=task_id,
    #     project_id=project_id,
    # )

    # creation, no wait needed
    labeling_task_id = __create_task_and_labels_for(
        project_id, "Reference Quality", ["Good", "Needs fix"]
    )
    __load_bricks_from_group("some group", labeling_task_id)

    labeling_task_id = __create_task_and_labels_for(
        project_id, "Reference Complexity", ["Low", "Medium", "High"]
    )
    __load_bricks_from_group("some group", labeling_task_id)

    labeling_task_id = __create_task_and_labels_for(
        project_id, "Reference Type", ["Unknown"]
    )

    labeling_task_id = __create_task_and_labels_for(
        project_id,
        "Personal Identifiable Information (PII)",
        ["Person", "Countries", "Date", "Time", "Organization"],
    )
    __load_bricks_from_group("some group", labeling_task_id)

    __create_attribute_with(
        project_id, LANGUAGE_DETECTION, "Language", enums.DataTypes.CATEGORY.value
    )
    __create_attribute_with(
        project_id,
        REFERENCE_CHUNKS,
        "reference_chunks",
        enums.DataTypes.EMBEDDING_LIST.value,
    )
    # websocket 10 %

    # wait for tokenization to finish

    # run attribute & wait for tokenization to finish

    # run attribute & wait for tokenization to finish

    # run embeddings & wait

    # create outlier slice for both embeddings

    # run all heuristics & check state for finish


def __create_task_and_labels_for(
    project_id: str,
    task_name: str,
    labels: List[str],
    task_type: Optional[str] = None,
    target_attribute_id: Optional[str] = None,
) -> str:
    if task_type is None:
        task_type = enums.LabelingTaskType.CLASSIFICATION.value
    task_item = labeling_task_manager.create_labeling_task(
        project_id, task_name, task_type, target_attribute_id
    )
    label_manager.create_labels(project_id, str(task_item.id), labels)
    return str(task_item.id)


def __load_bricks_from_group(group_key: str, target_task_id) -> List[str]:
    print("can't load bricks from group", flush=True)


def __create_attribute_with(project_id: str, code: str, name: str, attribute_type: str):
    attribute_item = attribute_manager.create_user_attribute(
        project_id, name, attribute_type
    )
    attribute_item.source_code = code
    general.commit()
