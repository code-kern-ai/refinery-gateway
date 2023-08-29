import os
from typing import List, Optional, Dict, Any

from util import service_requests

BASE_URI = os.getenv("NEURAL_SEARCH")


def request_most_similar_record_ids(
    project_id: str,
    embedding_id: str,
    record_id: str,
    limit: int,
    att_filter: Optional[List[Dict[str, Any]]] = None,
    record_sub_key: Optional[int] = None,
) -> List[str]:
    url = f"{BASE_URI}/most_similar?project_id={project_id}&embedding_id={embedding_id}&record_id={record_id}&limit={limit}"
    if record_sub_key is not None:
        url += f"&record_sub_key={record_sub_key}"

    result = service_requests.post_call_or_raise(url, att_filter)
    return result
