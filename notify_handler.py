from typing import Dict

import requests
import traceback

from submodules.model import daemon


def notify_others_about_change(notify: Dict[str, str]) -> None:

    for key in notify:
        url = f"{notify[key]}/config_changed"
        try:
            response = requests.put(url)
            if response.status_code != 200:
                print(f"couldn't notify - code:{response.status_code}", key, flush=True)
        except requests.exceptions.ConnectionError:
            print("couldn't notify", key, flush=True)
        except Exception:
            print(traceback.format_exc(), flush=True)


def notify_others_about_change_thread(notify: Dict[str, str]) -> None:
    # needs to be threaded to work with circular requests (this notifies about changes -> service requests full config from this)
    daemon.run_without_db_token(notify_others_about_change, notify)
