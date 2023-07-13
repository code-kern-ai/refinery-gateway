from typing import Optional

import graphene

from controller.auth import manager as auth
from graphql_api.types import Project
from submodules.model import enums, events
from controller.project import manager
from util import doc_ock, notification
from submodules.model.business_objects import notification as notification_model
from submodules.model import enums


class CreateProject(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=False)
        description = graphene.String(required=False)

    ok = graphene.Boolean()
    project = graphene.Field(lambda: Project)

    def mutate(
        self, info, name: Optional[str] = None, description: Optional[str] = None
    ):
        auth.check_demo_access(info)
        user = auth.get_user_by_info(info)
        organization = auth.get_organization_id_by_info(info)
        project = manager.create_project(
            organization.id, name, description, str(user.id)
        )
        notification.send_organization_update(
            project.id, f"project_created:{str(project.id)}", True
        )
        doc_ock.post_event(
            str(user.id),
            events.CreateProject(Name=f"{name}-{project.id}", Description=description),
        )
        return CreateProject(project=project, ok=True)


class CreateSampleProject(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=False)
        project_type = graphene.String(required=False)

    ok = graphene.Boolean()
    project = graphene.Field(lambda: Project)

    def mutate(
        self, info, name: Optional[str] = None, project_type: Optional[str] = None
    ):
        auth.check_demo_access(info)
        user = auth.get_user_by_info(info)
        organization = auth.get_organization_id_by_info(info)
        project = manager.import_sample_project(
            user.id, organization.id, name, project_type
        )
        doc_ock.post_event(
            str(user.id),
            events.CreateProject(
                Name=f"{project.name}-{project.id}", Description=project.description
            ),
        )

        return CreateSampleProject(project=project, ok=True)


class DeleteProject(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.update_project(project_id, status=enums.ProjectStatus.IN_DELETION.value)
        user = auth.get_user_by_info(info)
        project_item = manager.get_project(project_id)
        organization_id = str(project_item.organization_id)
        notification.create_notification(
            enums.NotificationType.PROJECT_DELETED, user.id, None, project_item.name
        )
        notification_model.remove_project_connection_for_last_x(project_id)
        manager.delete_project(project_id)
        notification.send_organization_update(
            project_id, f"project_deleted:{project_id}", True, organization_id
        )
        return DeleteProject(ok=True)


class UpdateProjectStatus(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        new_status = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, new_status: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.update_project(project_id, status=new_status)
        return UpdateProjectStatus(ok=True)


class UpdateProjectNameAndDescription(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        name = graphene.String()
        description = graphene.String()

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.update_project(project_id, name=name, description=description)
        # one global for e.g notification center
        notification.send_organization_update(
            project_id, f"project_update:{project_id}", True
        )
        # one for the specific project so it's updated
        notification.send_organization_update(
            project_id, f"project_update:{project_id}"
        )
        return UpdateProjectNameAndDescription(ok=True)


class UpdateProjectTokenizer(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        tokenizer = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, tokenizer: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.update_project(project_id, tokenizer=tokenizer)
        return UpdateProjectTokenizer(ok=True)


class UpdateProjectForGates(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_by_info(info).id
        manager.update_project_for_gates(project_id, user_id)
        return UpdateProjectForGates(ok=True)


class ProjectMutation(graphene.ObjectType):
    create_project = CreateProject.Field()
    create_sample_project = CreateSampleProject.Field()
    delete_project = DeleteProject.Field()
    update_project_status = UpdateProjectStatus.Field()
    update_project_name_and_description = UpdateProjectNameAndDescription.Field()
    update_project_tokenizer = UpdateProjectTokenizer.Field()
    update_project_for_gates = UpdateProjectForGates.Field()
