from controller.auth import manager as auth
from controller.upload_task import manager as task_manager
import graphene


class SetUploadMappings(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        upload_task_id = graphene.ID(required=True)
        mappings = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, upload_task_id: str, mappings: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        task_manager.update_task(project_id, upload_task_id, mappings=mappings)
        return SetUploadMappings(ok=True)


class UploadTaskMutation(graphene.ObjectType):
    set_upload_mappings = SetUploadMappings.Field()
