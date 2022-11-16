import uuid
from typing import Dict

from submodules.model import enums
from submodules.model.business_objects import user


def create_unknown_users(user_mapping: Dict) -> Dict:
    result_mapping = {}
    for label_studio_id, mapping in user_mapping.items():
        if mapping == enums.RecordImportMappingValues.UNKNOWN.value:
            user_id = str(uuid.uuid4())
            user.create(user_id=user_id)
            result_mapping[label_studio_id] = user_id
        else:
            result_mapping[label_studio_id] = mapping
    return result_mapping
