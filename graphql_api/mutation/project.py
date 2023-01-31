import os
from typing import Optional
from controller.tokenization import tokenization_service

import graphene

from controller.auth import manager as auth
from graphql_api import types
from graphql_api.types import Project
from submodules.model import enums, events
from controller.project import manager
from submodules.s3.controller import bucket_exists, create_bucket
from util import doc_ock, notification
from submodules.model.business_objects import notification as notification_model


from controller.transfer.record_transfer_manager import import_records_and_rlas
from controller.transfer.manager import check_and_add_running_id
from controller.auth import manager as auth_manager
from controller.project import manager as project_manager
from controller.upload_task import manager as upload_task_manager
from submodules.model import enums
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

__engine = None


def get_workflow_db_engine():
    global __engine
    if __engine is None:
        __engine = create_engine(os.getenv("WORKFLOW_POSTGRES"))
    return __engine


class CreateProject(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String(required=False)

    ok = graphene.Boolean()
    project = graphene.Field(lambda: Project)

    def mutate(self, info, name: str, description: Optional[str] = None):
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
            user,
            events.CreateProject(Name=f"{name}-{project.id}", Description=description),
        )
        return CreateProject(project=project, ok=True)


class CreateProjectByWorkflowStore(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String(required=True)
        tokenizer = graphene.String(required=True)
        storeId = graphene.String(required=True)

    ok = graphene.Boolean()
    project = graphene.Field(lambda: Project)

    def mutate(self, info, name: str, description: str, tokenizer: str, storeId: str):
        user = auth.get_user_by_info(info)
        organization = auth_manager.get_organization_by_user_id(user.id)

        if not bucket_exists(str(organization.id)):
            create_bucket(str(organization.id))

        project = project_manager.create_project(
            organization.id, name, description, user.id
        )
        project_manager.update_project(project_id=project.id, tokenizer=tokenizer)

        Session = sessionmaker(get_workflow_db_engine())
        with Session() as session:
            results = session.execute(
                f"SELECT record FROM store_entry WHERE store_id = '{storeId}'"
            ).all()

        data = [result for result, in results]

        upload_task = upload_task_manager.create_upload_task(
            user_id=user.id,
            project_id=project.id,
            file_name=name,
            file_type="json",
            file_import_options="",
            upload_type=enums.UploadTypes.WORKFLOW_STORE.value,
        )
        import_records_and_rlas(
            project.id,
            user.id,
            data,
            upload_task,
            enums.RecordCategory.SCALE.value,
        )
        check_and_add_running_id(project.id, user.id)

        upload_task_manager.update_upload_task_to_finished(upload_task)
        tokenization_service.request_tokenize_project(str(project.id), str(user.id))

        notification.send_organization_update(
            project.id, f"project_created:{str(project.id)}", True
        )
        doc_ock.post_event(
            user,
            events.CreateProject(Name=f"{name}-{project.id}", Description=description),
        )

        return CreateProjectByWorkflowStore(project=project, ok=True)


class CreateSampleProject(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=False)

    ok = graphene.Boolean()
    project = graphene.Field(lambda: Project)

    def mutate(self, info, name: Optional[str] = None):
        auth.check_demo_access(info)
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


class ProjectMutation(graphene.ObjectType):
    create_project = CreateProject.Field()
    create_project_by_workflow_store = CreateProjectByWorkflowStore.Field()
    create_sample_project = CreateSampleProject.Field()
    delete_project = DeleteProject.Field()
    update_project_status = UpdateProjectStatus.Field()
    update_project_name_and_description = UpdateProjectNameAndDescription.Field()
    update_project_tokenizer = UpdateProjectTokenizer.Field()
