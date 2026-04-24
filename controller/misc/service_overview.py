import datetime
from enum import Enum
from typing import Any, Dict

from submodules.model.business_objects import app_version


class Service(Enum):
    AC_EXEC_ENV = "AC_EXEC_ENV"
    ADMIN_DASHBOARD = "ADMIN_DASHBOARD"
    AUTHORIZER = "AUTHORIZER"
    EMBEDDER = "EMBEDDER"
    ENTRY = "ENTRY"
    GATEWAY = "GATEWAY"
    LF_EXEC_ENV = "LF_EXEC_ENV"
    ML_EXEC_ENV = "ML_EXEC_ENV"
    MODEL_PROVIDER = "MODEL_PROVIDER"
    NEURAL_SEARCH = "NEURAL_SEARCH"
    TOKENIZER = "TOKENIZER"
    UI = "UI"
    UPDATER = "UPDATER"
    WEAK_SUPERVISOR = "WEAK_SUPERVISOR"
    WEBSOCKET = "WEBSOCKET"
    UNKNOWN = "UNKNOWN"


__service_lookup = {
    Service.AC_EXEC_ENV: {
        "name": "AC Exec Env",
        "link": "https://github.com/code-kern-ai/refinery-ac-exec-env",
        "public_repo": True,
    },
    Service.ADMIN_DASHBOARD: {
        "name": "Admin Dashboard",
        "link": "https://github.com/code-kern-ai/admin-dashboard",
        "public_repo": False,
    },
    Service.AUTHORIZER: {
        "name": "Authorizer",
        "link": "https://github.com/code-kern-ai/refinery-authorizer",
        "public_repo": True,
    },
    Service.EMBEDDER: {
        "name": "Embedder",
        "link": "https://github.com/code-kern-ai/refinery-embedder",
        "public_repo": True,
    },
    Service.ENTRY: {
        "name": "Entry",
        "link": "https://github.com/code-kern-ai/refinery-entry",
        "public_repo": True,
    },
    Service.GATEWAY: {
        "name": "Gateway",
        "link": "https://github.com/code-kern-ai/refinery-gateway",
        "public_repo": True,
    },
    Service.LF_EXEC_ENV: {
        "name": "LF Exec Env",
        "link": "https://github.com/code-kern-ai/refinery-lf-exec-env",
        "public_repo": True,
    },
    Service.ML_EXEC_ENV: {
        "name": "ML Exec Env",
        "link": "https://github.com/code-kern-ai/refinery-ml-exec-env",
        "public_repo": True,
    },
    Service.MODEL_PROVIDER: {
        "name": "Model Provider",
        "link": "https://github.com/code-kern-ai/refinery-model-provider",
        "public_repo": False,
    },
    Service.NEURAL_SEARCH: {
        "name": "Neural Search",
        "link": "https://github.com/code-kern-ai/refinery-neural-search",
        "public_repo": True,
    },
    Service.TOKENIZER: {
        "name": "Tokenizer",
        "link": "https://github.com/code-kern-ai/refinery-tokenizer",
        "public_repo": True,
    },
    Service.UI: {
        "name": "UI",
        "link": "https://github.com/code-kern-ai/refinery-ui",
        "public_repo": True,
    },
    Service.UPDATER: {
        "name": "Updater",
        "link": "https://github.com/code-kern-ai/refinery-updater",
        "public_repo": True,
    },
    Service.WEAK_SUPERVISOR: {
        "name": "Weak Supervisor",
        "link": "https://github.com/code-kern-ai/refinery-weak-supervisor",
        "public_repo": True,
    },
    Service.WEBSOCKET: {
        "name": "Websocket",
        "link": "https://github.com/code-kern-ai/refinery-websocket",
        "public_repo": True,
    },
    Service.UNKNOWN: {
        "name": "UNKNOWN",
        "link": "https://github.com/code-kern-ai",
        "public_repo": None,
    },
}


def can_check_remote(service: Service) -> bool:
    return __service_lookup[service]["public_repo"]


def get_services_info(only_public: bool) -> Dict[Service, Dict[str, Any]]:
    if not only_public:
        tmp = __service_lookup.copy()
    else:
        tmp = {k: v for k, v in __service_lookup.items() if v["public_repo"]}
    for service in tmp:
        if "key" not in tmp[service]:
            tmp[service]["key"] = service.value
    return tmp


def check_db_uptodate() -> bool:
    current_version = app_version.get_all()

    too_old = datetime.datetime.now() - datetime.timedelta(minutes=30)

    for db_entry in current_version:
        if not can_check_remote(Service[db_entry.service]):
            continue
        if db_entry.last_checked is None or db_entry.last_checked < too_old:
            return False
    return True
