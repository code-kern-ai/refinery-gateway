from typing import Any, Dict, List
from fast_api.types import ServiceVersionResult
from submodules.model.global_objects import (
    admin_queries as admin_queries_db_go,
)
from datetime import datetime
import os
from submodules.model import enums
from util.tmp_export_file_cleanup import add_cleanup_task
from uuid import uuid4
import pandas as pd
from submodules.model.util import ensure_sql_text
from submodules.model.business_objects import general


from util import service_requests

BASE_URI_UPDATER = os.getenv("UPDATER")


def get_version_overview() -> List[ServiceVersionResult]:
    updater_version_overview = __updater_version_overview()
    date_format = "%Y-%m-%dT%H:%M:%S.%f"  # 2022-09-06T12:10:39.167397
    return [
        {
            "service": service["name"],
            "installed_version": service["installed_version"],
            "remote_version": service["remote_version"],
            "last_checked": datetime.strptime(service["last_checked"], date_format),
            "remote_has_newer": service["remote_has_newer"],
            "link": service["link"],
        }
        for service in updater_version_overview
    ]


def has_updates() -> List[ServiceVersionResult]:
    return __updater_has_updates()


# function only sets the versions in the database, not the actual update logic
def update_versions_to_newest() -> None:
    return __update_versions_to_newest()


def __updater_version_overview() -> List[Dict[str, Any]]:
    url = f"{BASE_URI_UPDATER}/version_overview"
    return service_requests.get_call_or_raise(url)


def __updater_has_updates() -> bool:
    url = f"{BASE_URI_UPDATER}/has_updates"
    return service_requests.get_call_or_raise(url)


def __updater_update_to_newest() -> None:
    raise ValueError("This endpoint should only be called from the update batch script")


def __update_versions_to_newest() -> None:
    url = f"{BASE_URI_UPDATER}/update_versions_to_newest"
    return service_requests.post_call_or_raise(url, {})


def create_admin_query_excel(
    query: enums.AdminQueries, parameters: Dict[str, Any]
) -> str:

    q = admin_queries_db_go.get_result_admin_query(query, parameters, as_query=True)

    df = pd.read_sql(ensure_sql_text(q), con=general.get_bind())
    tmp_filename = f"tmp/feedback_{uuid4()}.xlsx"
    df.to_excel(tmp_filename, index=False)
    add_cleanup_task(tmp_filename, 5)
    return tmp_filename
