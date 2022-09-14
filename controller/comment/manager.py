from typing import Dict, Optional, Union
from submodules.model import enums

from submodules.model.business_objects import comments


def has_comments(
    xftype: str,
    xfkey: Optional[str] = None,
    project_id: Optional[str] = None,
    group_by_xfkey: bool = False,
) -> Union[bool, Dict[str, bool]]:

    try:
        xftype_parsed = enums.CommentCategory[xftype.upper()]
    except KeyError:
        raise ValueError(f"Invalid comment category: {xftype}")

    return comments.has_comments(xftype_parsed, xfkey, project_id, group_by_xfkey)
