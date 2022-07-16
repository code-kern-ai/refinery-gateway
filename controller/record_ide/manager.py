from typing import List

from util.record_ide import run_record_ide


def create_record_ide_payload(user_id: str, project_id: str, record_id: str, code: str) -> List[str]:
    return run_record_ide(user_id, project_id, record_id, code)
