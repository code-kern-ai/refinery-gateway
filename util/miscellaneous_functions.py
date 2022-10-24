from itertools import islice
from typing import Dict, Any, Iterator, Optional


def chunk_dict(data: Dict, SIZE: Optional[int] = 1000) -> Iterator[Dict[str, Any]]:
    it = iter(data)
    for i in range(0, len(data), SIZE):
        yield {k: data[k] for k in islice(it, SIZE)}


def first_item(data: Dict[str, Any]) -> Any:
    for e in data:
        return data[e]
