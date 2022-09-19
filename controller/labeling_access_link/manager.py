from datetime import datetime
from typing import List, Optional
from submodules.model import enums
from submodules.model.models import LabelingAccessLink
from submodules.model.business_objects import (
    general,
    labeling_access_link,
    information_source,
)


def get(link_id: str) -> LabelingAccessLink:
    return labeling_access_link.get(link_id)


def get_ensure_access(link_id: str) -> LabelingAccessLink:
    return labeling_access_link.get_ensure_access(link_id)


def get_by_all_by_project_id(project_id: str) -> List[LabelingAccessLink]:
    return labeling_access_link.get_by_all_by_project_id(project_id)


def get_by_all_by_user_id(user_id: str) -> List[LabelingAccessLink]:
    return labeling_access_link.get_by_all_by_user_id(user_id)


def generate_heuristic_access_link(
    project_id: str, created_by: str, heuristic_id: str
) -> LabelingAccessLink:
    information_source_item = information_source.get(project_id, heuristic_id)
    if not information_source_item:
        raise ValueError(f"Invalid Heuristic ID: {heuristic_id}")
    if information_source_item.type != enums.InformationSourceType.CROWD_LABELER.value:
        raise ValueError(f"Heuristic {heuristic_id} not meant for crowd labeling")

    link = f"/projects/{project_id}/labeling/{heuristic_id}?pos=1&type={enums.LinkTypes.HEURISTIC.value}"
    return labeling_access_link.create(
        project_id,
        link,
        enums.LinkTypes.HEURISTIC,
        created_by,
        heuristic_id=heuristic_id,
        with_commit=True,
    )


def generate_data_slice_access_link(
    project_id: str, created_by: str, slice_id: str
) -> LabelingAccessLink:
    link = f"/projects/{project_id}/labeling/{slice_id}?pos=1&type={enums.LinkTypes.DATA_SLICE.value}"
    return labeling_access_link.create(
        project_id,
        link,
        enums.LinkTypes.DATA_SLICE,
        created_by,
        data_slice_id=slice_id,
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


def remove(link_id: str) -> str:
    link = labeling_access_link.get(link_id)
    to_return = str(link.heuristic_id) if link.heuristic_id else str(link.data_slice_id)
    labeling_access_link.remove(link_id, True)
    return to_return


def change_user_access_to_link_lock(link_id: str, lock_state: bool) -> str:
    link = labeling_access_link.get(link_id)
    if link:
        link.is_locked = lock_state
        general.commit()
        return_id = (
            link.heuristic_id
            if link.link_type == enums.LinkTypes.HEURISTIC.value
            else link.data_slice_id
        )
        return str(return_id)


def check_link_locked(project_id: str, link_route: str) -> bool:
    if link_route.find("00000000-0000-0000-0000-000000000000") > -1:
        # dummy session
        return False
    item = labeling_access_link.get_by_link(project_id, link_route)
    if not item:
        # deleted
        return True
    return item.is_locked
