from typing import Optional

import graphene

from controller.auth import manager as auth
from graphql_api import types
from graphql_api.types import Project
from submodules.model import enums, events
from controller.project import manager
from util import doc_ock, notification


class CreateProject(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String(required=False)

    ok = graphene.Boolean()
    project = graphene.Field(lambda: Project)

    def mutate(self, info, name: str, description: Optional[str] = None):
        auth.check_is_demo()
        user = auth.get_user_by_info(info)
        organization = auth.get_organization_id_by_info(info)
        project = manager.create_project(
            organization.id, name, description, str(user.id)
        )
        notification.send_organization_update(project.id, "project_created", True)
        doc_ock.post_event(
            user,
            events.CreateProject(Name=f"{name}-{project.id}", Description=description),
        )
        return CreateProject(project=project, ok=True)


class CreateSampleProject(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=False)

    ok = graphene.Boolean()
    project = graphene.Field(lambda: Project)

    def mutate(self, info, name: Optional[str] = None):
        auth.check_is_demo()
        user = auth.get_user_by_info(info)
        organization = auth.get_organization_id_by_info(info)
        project = manager.import_sample_project(user.id, organization.id, name)
        doc_ock.post_event(
            user,
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
        auth.check_is_demo()
        auth.check_project_access(info, project_id)
        manager.update_project(project_id, status=enums.ProjectStatus.IN_DELETION.value)
        user = auth.get_user_by_info(info)
        project_item = manager.get_project(project_id)
        organization_id = str(project_item.organization_id)
        notification.create_notification(
            enums.NotificationType.PROJECT_DELETED, user.id, None, project_item.name
        )
        notification.send_organization_update(
            project_id, f"project_deleted:{project_id}", True, organization_id
        )
        manager.delete_project(project_id)
        return DeleteProject(ok=True)


class UpdateProjectStatus(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        new_status = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, new_status: str):
        auth.check_is_demo()
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
        auth.check_is_demo()
        auth.check_project_access(info, project_id)
        manager.update_project(project_id, name=name, description=description)
        # one global for e.g notification center
        notification.send_organization_update(project_id, "project_update", True)
        # one for the specific project so it's updated
        notification.send_organization_update(project_id, "project_update")
        return UpdateProjectNameAndDescription(ok=True)


class UpdateProjectTokenizer(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        tokenizer = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, tokenizer: str):
        auth.check_is_demo()
        auth.check_project_access(info, project_id)
        manager.update_project(project_id, tokenizer=tokenizer)
        return UpdateProjectTokenizer(ok=True)


class ProjectMutation(graphene.ObjectType):
    create_project = CreateProject.Field()
    create_sample_project = CreateSampleProject.Field()
    delete_project = DeleteProject.Field()
    update_project_status = UpdateProjectStatus.Field()
    update_project_name_and_description = UpdateProjectNameAndDescription.Field()
    update_project_tokenizer = UpdateProjectTokenizer.Field()
