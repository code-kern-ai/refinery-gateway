import logging

from submodules.model.enums import UploadStates


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NoUploadTaskInStateFound(Exception):
    def __init__(
        self,
        upload_task_id: str,
        project_id: str,
        file_name: str,
        upload_state: UploadStates,
    ):
        self.message = f"No upload task was found for ID: {upload_task_id} and Project ID: {project_id} and file: {file_name} with state: {upload_state}."
        logger.error(self.message)
        super().__init__(self.message)


class NotAllowedUploadSource(Exception):
    def __init__(
        self, upload_source: str, project_id: str, file_name: str,
    ):
        self.message = f"Upload source was not allowed. Upload source: {upload_source} for Project ID: {project_id} and file: {file_name}."
        logger.error(self.message)
        super().__init__(self.message)
