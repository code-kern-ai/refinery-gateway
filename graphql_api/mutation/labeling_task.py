from typing import Optional

from controller.auth import manager as auth
from controller.labeling_task import manager
from controller.project import manager as project_manager
from submodules.model import events
from util import doc_ock, notification
import graphene


class CreateLabelingTask(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        labeling_task_name = graphene.String(required=True)
        labeling_task_type = graphene.String(required=True)
        labeling_task_target_id = graphene.ID(required=False)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        labeling_task_name: str,
        labeling_task_type: str,
        labeling_task_target_id: Optional[str] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        project = project_manager.get_project(project_id)
        item = manager.create_labeling_task(
            project_id, labeling_task_name, labeling_task_type, labeling_task_target_id
        )
        doc_ock.post_event(
            user,
            events.AddLabelingTask(
                ProjectName=f"{project.name}-{project.id}",
                Name=labeling_task_name,
                Type=labeling_task_type,
            ),
        )
        notification.send_organization_update(
            project_id, f"labeling_task_created:{str(item.id)}"
        )
        return CreateLabelingTask(ok=True)


class UpdateLabelingTask(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        labeling_task_id = graphene.ID(required=True)
        labeling_task_name = graphene.String(required=False)
        labeling_task_type = graphene.String(required=False)
        labeling_task_target_id = graphene.ID(required=False)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        labeling_task_id: str,
        labeling_task_name: str,
        labeling_task_type: str,
        labeling_task_target_id: Optional[str] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.update_labeling_task(
            project_id,
            labeling_task_id,
            labeling_task_target_id,
            labeling_task_name,
            labeling_task_type,
        )
        notification.send_organization_update(
            project_id, f"labeling_task_updated:{labeling_task_id}:{labeling_task_type}"
        )

        return UpdateLabelingTask(ok=True)


class DeleteLabelingTask(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        labeling_task_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, labeling_task_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.delete_labeling_task(project_id, labeling_task_id)
        notification.send_organization_update(
            project_id, f"labeling_task_deleted:{labeling_task_id}"
        )

        return DeleteLabelingTask(ok=True)


class LabelingTaskMutation(graphene.ObjectType):
    create_labeling_task = CreateLabelingTask.Field()
    update_labeling_task = UpdateLabelingTask.Field()
    delete_labeling_task = DeleteLabelingTask.Field()
