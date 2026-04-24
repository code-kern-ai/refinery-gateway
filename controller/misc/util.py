# Migrated from refinery-updater/util.py (no HTTP to refinery-updater; no data-migration loop here).
from datetime import datetime
from typing import Any, Dict, List, Union

import git
from submodules.model.business_objects import app_version, general
from submodules.model.enums import try_parse_enum_value
from submodules.model.models import AppVersion
from controller.misc.service_overview import (
    Service,
    check_db_uptodate,
    get_services_info,
)


def is_newer(v1: str, v2: str) -> bool:
    a = [__get_int_from_string(x) for x in v1.split(".")]
    b = [__get_int_from_string(x) for x in v2.split(".")]
    if len(a) != len(b) and len(a) != 3:
        raise Exception("invalid version format")
    return __is_newer_int(a, b)


def __get_int_from_string(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def __is_newer_int(v1: List[int], v2: List[int]) -> bool:
    for idx, _ in enumerate(v1):
        if v2[idx] > v1[idx]:
            return False
        elif v2[idx] < v1[idx]:
            return True
    return False


def __last_tag(repo_link: str) -> Any:
    try:
        g = git.cmd.Git()
        blob = g.ls_remote(repo_link, sort="-v:refname", tags=True)
        if len(blob) == 0:
            return "0.0.0"
        tag = blob.split("\n")[0].split("/")[-1]
        if tag[0] == "v":
            return tag[1:]
        return tag
    except Exception:
        return "0.0.0"


def version_overview() -> List[Dict[str, Any]]:
    current_version = app_version.get_all()
    if len(current_version) == 0:
        print(
            "version check before entry add --> update to current version", flush=True
        )
        update_to_newest()

    if not check_db_uptodate():
        print("need to update db", flush=True)
        check_has_newer_version()
    # Always re-fetch: after empty-DB + update_to_newest, old local list can be stale
    # (updater also only refreshed in the "need to update db" branch).
    current_version = app_version.get_all()

    lookup_dict = get_services_info(False)
    return [
        {
            "name": lookup_dict[Service[x.service]]["name"],
            "link": lookup_dict[Service[x.service]]["link"],
            "public_repo": lookup_dict[Service[x.service]]["public_repo"],
            "installed_version": check_if_version_exists(
                x.installed_version, x.remote_version, False
            ),
            "remote_version": check_if_version_exists(
                x.installed_version, x.remote_version, True
            ),
            "remote_has_newer": __remote_has_newer(
                x.installed_version, x.remote_version
            ),
            "last_checked": x.last_checked,
        }
        for x in current_version
        if Service.__members__.get(x.service) is not None
    ]


def has_updates() -> bool:
    if not check_db_uptodate():
        print("need to update db", flush=True)
        check_has_newer_version()
    current_version = app_version.get_all()
    return any(
        __remote_has_newer(db_entry.installed_version, db_entry.remote_version)
        for db_entry in current_version
    )


def update_to_newest():
    something_updated = False
    current_version = app_version.get_all()
    if len(current_version) == 0:
        print(
            "No version found in database -> assuming new installation or version < 1.2.0",
            flush=True,
        )
        init_versions()
        something_updated = True
        current_version = app_version.get_all()
    if not check_db_uptodate():
        print("checking remote", flush=True)
        # Refreshes remote_version / last_checked (and commits inside); must count as "updated" for the caller.
        check_has_newer_version()
        current_version = app_version.get_all()
    for db_entry in current_version:
        if __remote_has_newer(db_entry.installed_version, db_entry.remote_version):
            db_entry.installed_version = db_entry.remote_version
            something_updated = True
    if something_updated:
        general.commit()
    return something_updated


def check_has_newer_version() -> bool:
    current_version = app_version.get_all()
    if len(current_version) == 0:
        print("version check before entry add --> shouldn't happen", flush=True)
        return False
    lookup_dict = get_services_info(True)
    diff_version = False
    for db_entry in current_version:
        x = try_parse_enum_value(db_entry.service, Service, False)
        if x in lookup_dict:
            link = lookup_dict[x]["link"]
            remote_version = __last_tag(link)
            db_entry.last_checked = datetime.now()
            db_entry.remote_version = remote_version
            if __remote_has_newer(db_entry.installed_version, remote_version):
                diff_version = True
                print(
                    "newer version found for "
                    + db_entry.service
                    + " (used: "
                    + db_entry.installed_version
                    + ", remote: "
                    + remote_version
                    + ")"
                )

    general.commit()
    return diff_version


def __remote_has_newer(installed: str, remote: Union[str, None]) -> bool:
    if remote is None:
        return None

    return is_newer(remote, installed)


def check_if_version_exists(installed: str, remote: str, is_remote: bool) -> str:
    if "0.0.0" in [installed, remote]:
        return "unknown"
    if is_remote:
        return remote
    else:
        return installed


def init_versions() -> None:
    print("add service entries...")
    entries = get_services_info(True)
    general.add_all(
        [
            AppVersion(service=entries[k]["key"], installed_version="1.2.0")
            for k in entries
        ],
        True,
    )
    print("upgrade done")


def update_versions_to_newest() -> None:
    general.execute(
        f"""
        UPDATE app_version
        SET installed_version = remote_version
        WHERE installed_version != remote_version
        """
    )
    general.commit()
