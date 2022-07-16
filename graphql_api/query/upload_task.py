import graphene

from controller.auth import manager as auth
from controller.upload_task import manager
from graphql_api.types import UploadTask


class UploadTaskQuery(graphene.ObjectType):

    upload_task_by_id = graphene.Field(
        UploadTask,
        project_id=graphene.ID(required=True),
        upload_task_id=graphene.ID(required=True),
    )

    def resolve_upload_task_by_id(
        self, info, project_id: str, upload_task_id: str
    ) -> UploadTask:
        auth.check_project_access(info, project_id)
        if upload_task_id.find("/") != -1:
            upload_task_id = upload_task_id.split("/")[-1]
        return manager.get_upload_task(project_id, upload_task_id)
