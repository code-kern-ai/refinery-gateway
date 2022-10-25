from itertools import islice
from typing import Dict, Any, Iterator, List, Optional
from submodules.model.business_objects.export import OUTSIDE_CONSTANT

from submodules.model.models import LabelingTask


def chunk_dict(data: Dict, SIZE: int = 1000) -> Iterator[Dict[str, Any]]:
    it = iter(data)
    for i in range(0, len(data), SIZE):
        yield {k: data[k] for k in islice(it, SIZE)}


def chunk_list(list: List, SIZE: int = 1000) -> Iterator[List[Any]]:
    return (list[pos : pos + SIZE] for pos in range(0, len(list), SIZE))


def first_item(data: Dict[str, Any]) -> Any:
    for e in data:
        return data[e]


def get_max_length_of_task_labels(task: LabelingTask) -> int:
    max_len = len(max([l.name for l in task.labels], key=len)) + 2
    if max_len < len(OUTSIDE_CONSTANT):
        return len(OUTSIDE_CONSTANT)
    return max_len
