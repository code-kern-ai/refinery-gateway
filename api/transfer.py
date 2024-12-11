import logging
import traceback
from typing import Optional
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse

from submodules.model.business_objects import (
    general,
)

from controller.transfer import manager as transfer_manager
from controller.upload_task import manager as upload_task_manager
from controller.auth import manager as auth_manager
from controller.project import manager as project_manager
from submodules.model import enums, exceptions
from util.notification import create_notification
from submodules.model.enums import NotificationType
from submodules.model.models import UploadTask
from util import notification


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class JSONImport(HTTPEndpoint):
    async def post(self, request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        request_body = await request.json()
        user_id = request_body["user_id"]
        auth_manager.check_project_access_from_user_id(user_id, project_id)

        records = request_body["records"]

        project = project_manager.get_project(project_id)
        num_project_records = len(project.records)
        for att in project.attributes:
            if att.is_primary_key:
                for idx, record in enumerate(records):
                    if att.name not in record:
                        if att.name == "running_id":
                            records[idx][att.name] = num_project_records + idx + 1
                        else:
                            raise exceptions.InvalidInputException(
                                f"Non-running-id, primary key {att.name} missing in record"
                            )

        transfer_manager.import_records_from_json(
            project_id,
            user_id,
            records,
            request_body["request_uuid"],
            request_body["is_last"],
        )
        return JSONResponse({"success": True})
