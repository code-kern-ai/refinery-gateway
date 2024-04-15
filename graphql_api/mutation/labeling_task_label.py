from graphql_api.types import Label
from submodules.model import events
from controller.labeling_task_label import manager
from controller.labeling_task import manager as task_manager
import graphene
from controller.auth import manager as auth
from controller.project import manager as project_manager
from util import doc_ock, notification
from typing import Dict, List


class CreateLabelingTaskLabel(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        labeling_task_id = graphene.ID(required=True)
        label_name = graphene.String(required=True)
        label_color = graphene.String(required=False)

    label = graphene.Field(lambda: Label)

    def mutate(
        self,
        info,
        project_id: str,
        labeling_task_id: str,
        label_name: str,
        label_color: str = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        label = manager.create_label(
            project_id, label_name, labeling_task_id, label_color
        )
        task = task_manager.get_labeling_task(project_id, labeling_task_id)
        project = project_manager.get_project(project_id)
        doc_ock.post_event(
            str(user.id),
            events.AddLabel(
                ProjectName=f"{project.name}-{project.id}",
                Name=label_name,
                LabelingTaskName=task.name,
            ),
        )
        notification.send_organization_update(
            project_id, f"label_created:{label.id}:labeling_task:{labeling_task_id}"
        )

        return CreateLabelingTaskLabel(label=label)


class CreateLabelingTaskLabels(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        labeling_task_id = graphene.ID(required=True)
        labels = graphene.List(graphene.String, required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, labeling_task_id: str, labels: List[str]):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        created_labels = manager.create_labels(project_id, labeling_task_id, labels)
        task = task_manager.get_labeling_task(project_id, labeling_task_id)
        project = project_manager.get_project(project_id)
        for label in created_labels:
            doc_ock.post_event(
                str(user.id),
                events.AddLabel(
                    ProjectName=f"{project.name}-{project_id}",
                    Name=label.name,
                    LabelingTaskName=task.name,
                ),
            )
            notification.send_organization_update(
                project_id, f"label_created:{label.id}:labeling_task:{labeling_task_id}"
            )

        return CreateLabelingTaskLabels(ok=True)


class UpdateLabelingTaskLabelColor(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        labeling_task_label_id = graphene.ID(required=True)
        label_color = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(
        self, info, project_id: str, labeling_task_label_id: str, label_color: str
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.update_label_color(project_id, labeling_task_label_id, label_color)
        return UpdateLabelingTaskLabelColor(ok=True)


class UpdateLabelingTaskLabelHotkey(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        labeling_task_label_id = graphene.ID(required=True)
        label_hotkey = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(
        self, info, project_id: str, labeling_task_label_id: str, label_hotkey: str
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.update_label_hotkey(project_id, labeling_task_label_id, label_hotkey)
        return UpdateLabelingTaskLabelColor(ok=True)


class UpdateLabelingTaskLabelName(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        labeling_task_label_id = graphene.ID(required=True)
        new_name = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, labeling_task_label_id: str, new_name: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.update_label_name(project_id, labeling_task_label_id, new_name)
        return UpdateLabelingTaskLabelColor(ok=True)


class HandleLabelRenameWarnings(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        warning_data = graphene.JSONString(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, warning_data: Dict[str, str]):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.handle_label_rename_warning(project_id, warning_data)
        return UpdateLabelingTaskLabelColor(ok=True)


class DeleteLabelingTaskLabel(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        label_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, label_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        label = manager.get_label(project_id, label_id)
        labeling_task_id = label.labeling_task_id
        manager.delete_label(project_id, label_id)
        notification.send_organization_update(
            project_id, f"label_deleted:{label_id}:labeling_task:{labeling_task_id}"
        )
        return DeleteLabelingTaskLabel(ok=True)


class LabelingTaskLabelMutation(graphene.ObjectType):
    create_label = CreateLabelingTaskLabel.Field()
    create_labels = CreateLabelingTaskLabels.Field()
    delete_label = DeleteLabelingTaskLabel.Field()
    update_label_color = UpdateLabelingTaskLabelColor.Field()
    update_label_hotkey = UpdateLabelingTaskLabelHotkey.Field()
    update_label_name = UpdateLabelingTaskLabelName.Field()
    handle_label_rename_warnings = HandleLabelRenameWarnings.Field()
