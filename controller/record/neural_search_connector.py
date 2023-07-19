import os
from typing import List

from util import service_requests

BASE_URI = os.getenv("NEURAL_SEARCH")


def request_most_similar_record_ids(
    project_id: str, embedding_id: str, record_id: str, limit: int
) -> List[str]:
    url = f"{BASE_URI}/most_similar?project_id={project_id}&embedding_id={embedding_id}&record_id={record_id}&limit={limit}"

    # changed from get to post so we can send the filter -> however currently filter isn't part of the prototype so None
    result = service_requests.post_call_or_raise(url, None)
    return result
