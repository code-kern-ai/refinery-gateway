from submodules.model import LabelingTask
from submodules.model.enums import InformationSourceReturnType, LabelingTaskType


def resolve_source_return_type(labeling_task: LabelingTask) -> str:
    if labeling_task.task_type == LabelingTaskType.INFORMATION_EXTRACTION.value:
        return_type: str = InformationSourceReturnType.YIELD.value
    else:
        return_type: str = InformationSourceReturnType.RETURN.value
    return return_type
