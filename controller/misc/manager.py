import controller.misc.util as util
from typing import Any, Dict, List, Optional
from fast_api.types import ServiceVersionResult
from submodules.model.global_objects import (
    admin_queries as admin_queries_db_go,
)
from datetime import datetime
from submodules.model import enums
from util.tmp_export_file_cleanup import add_cleanup_task
from uuid import uuid4
import pandas as pd
from submodules.model.util import ensure_sql_text
from submodules.model.business_objects import general

_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


def get_version_overview() -> List[ServiceVersionResult]:
    rows = util.version_overview()
    return [
        {
            "service": service["name"],
            "installed_version": service["installed_version"],
            "remote_version": service["remote_version"],
            "last_checked": _parse_last_checked(service.get("last_checked")),
            "remote_has_newer": service["remote_has_newer"],
            "link": service["link"],
        }
        for service in rows
    ]


def _parse_last_checked(
    value: Any,
) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.strptime(value, _DATE_FORMAT)
    return None


def has_updates() -> bool:
    return util.has_updates()


def update_to_newest() -> bool:
    return util.update_to_newest()


# function only sets the versions in the database, not the actual update logic
def update_versions_to_newest() -> None:
    return util.update_versions_to_newest()


def create_admin_query_excel(
    query: enums.AdminQueries, parameters: Dict[str, Any]
) -> str:

    q = admin_queries_db_go.get_result_admin_query(query, parameters, as_query=True)

    df = pd.read_sql(ensure_sql_text(q), con=general.get_bind())
    tmp_filename = f"tmp/feedback_{uuid4()}.xlsx"
    df.to_excel(tmp_filename, index=False)
    add_cleanup_task(tmp_filename, 5)
    return tmp_filename
