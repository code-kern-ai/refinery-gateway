from typing import Optional

from util import notification


def send_log_message(
    sender_project_id: str,
    message: str,
    is_error: bool = False,
    organization_id: Optional[str] = None,
) -> None:
    state = "ERROR" if is_error else "INFO"
    notification.send_organization_update(
        sender_project_id,
        f"cognition_wizard:LOG_MESSAGE:{state}:{message}",
        organization_id=organization_id,
    )
