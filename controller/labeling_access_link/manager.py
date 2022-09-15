from datetime import datetime
from typing import List, Optional
from submodules.model import enums
from submodules.model.models import LabelingAccessLink
from submodules.model.business_objects import labeling_access_link, information_source


def get(link_id: str) -> LabelingAccessLink:
    return labeling_access_link.get(link_id)


def get_ensure_access(user_id: str, link_id: str) -> LabelingAccessLink:
    return labeling_access_link.get_ensure_access(user_id, link_id)


def get_by_all_by_project_id(project_id: str) -> List[LabelingAccessLink]:
    return labeling_access_link.get_by_all_by_project_id(project_id)


def get_by_all_by_user_id(user_id: str) -> List[LabelingAccessLink]:
    return labeling_access_link.get_by_all_by_user_id(user_id)


def get_by_all_by_project_user(
    project_id: str, user_id: str
) -> List[LabelingAccessLink]:
    return labeling_access_link.get_by_all_by_project_user(project_id, user_id)


def generate_heuristic_access_link(
    project_id: str, created_by: str, heuristic_id
) -> LabelingAccessLink:
    information_source_item = information_source.get(project_id, heuristic_id)
    if not information_source_item:
        raise ValueError(f"Invalid Heuristic ID: {heuristic_id}")
    if information_source_item.type != enums.InformationSourceType.CROWD_LABELER.value:
        raise ValueError(f"Heuristic {heuristic_id} not meant for crowd labeling")

    link = f"/app/projects/{project_id}/labeling/{heuristic_id}?pos=1&type={enums.LinkTypes.HEURISTIC.value}"
    return labeling_access_link.create(
        project_id,
        link,
        enums.LinkTypes.HEURISTIC,
        created_by,
        heuristic_id=heuristic_id,
        with_commit=True,
    )


def create(
    project_id: str,
    link: str,
    link_type: str,
    created_by: str,
    data_slice_id: Optional[str] = None,
    heuristic_id: Optional[str] = None,
) -> LabelingAccessLink:

    try:
        link_type_parsed = enums.LinkTypes[link_type.upper()]
    except KeyError:
        raise ValueError(f"Invalid LinkTypes: {link_type}")
    return labeling_access_link.create(
        project_id,
        link,
        link_type_parsed,
        created_by,
        data_slice_id,
        heuristic_id,
        None,
        True,
    )


def remove(link_id: str) -> None:
    return labeling_access_link.remove(link_id, True)


def change_user_access_to_link_lock(
    user_id: str, link_id: str, lock_state: bool
) -> bool:
    return labeling_access_link.change_user_access_to_link_lock(
        user_id, link_id, lock_state, True
    )
