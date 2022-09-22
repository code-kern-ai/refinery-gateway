from typing import Optional

from controller.auth import manager as auth
from controller.information_source import manager
import graphene
from graphql_api import types
from controller.auth.manager import get_user_by_info
from graphql_api.types import InformationSource
from submodules.model.enums import InformationSourceType
from util import notification


class CreateInformationSource(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        labeling_task_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        type = graphene.String(required=True)
        source_code = graphene.String()
        description = graphene.String()

    information_source = graphene.Field(InformationSource)

    def mutate(
        self,
        info,
        project_id: str,
        labeling_task_id: str,
        name: str,
        type: str,
        source_code: Optional[str] = None,
        description: Optional[str] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        if type == InformationSourceType.CROWD_LABELER.value:
            information_source = manager.create_crowd_information_source(
                str(user.id), project_id, labeling_task_id, name, description
            )

        else:
            information_source = manager.create_information_source(
                project_id,
                user.id,
                labeling_task_id,
                name,
                source_code,
                description,
                type,
            )
        notification.send_organization_update(project_id, f"information_source_created")
        return CreateInformationSource(information_source=information_source)


class DeleteInformationSource(graphene.Mutation):
    class Arguments:
        information_source_id = graphene.ID(required=True)
        project_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, information_source_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.delete_information_source(project_id, information_source_id)
        notification.send_organization_update(
            project_id, f"information_source_deleted:{information_source_id}"
        )
        return DeleteInformationSource(ok=True)


class ToggleInformationSource(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        information_source_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, information_source_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.toggle_information_source(project_id, information_source_id)
        notification.send_organization_update(
            project_id, f"information_source_updated:{information_source_id}"
        )
        return ToggleInformationSource(ok=True)


class SetAllInformationSourceSelected(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        value = graphene.Boolean(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, value: bool):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.set_all_information_source_selected(project_id, value)
        notification.send_organization_update(
            project_id, f"information_source_updated:all"
        )
        return ToggleInformationSource(ok=True)


class SetAllModelCallbacksSelected(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        value = graphene.Boolean(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, value: bool):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.set_all_model_callbacks_selected(project_id, value)
        # notification.send_organization_update(
        #     project_id, f"information_source_updated:all"
        # )
        return SetAllModelCallbacksSelected(ok=True)


class UpdateInformationSource(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        information_source_id = graphene.ID(required=True)
        labeling_task_id = graphene.ID(required=True)
        code = graphene.String()
        description = graphene.String()
        name = graphene.String()

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        information_source_id: str,
        labeling_task_id: str,
        code: Optional[str] = None,
        description: Optional[str] = None,
        name: Optional[str] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.update_information_source(
            project_id, information_source_id, labeling_task_id, code, description, name
        )
        user = auth.get_user_by_info(info)
        notification.send_organization_update(
            project_id, f"information_source_updated:{information_source_id}:{user.id}"
        )
        return UpdateInformationSource(ok=True)


class InformationSourceMutation(graphene.ObjectType):
    create_information_source = CreateInformationSource.Field()
    delete_information_source = DeleteInformationSource.Field()
    toggle_information_source = ToggleInformationSource.Field()
    update_information_source = UpdateInformationSource.Field()
    set_all_information_source_selected = SetAllInformationSourceSelected.Field()
    set_all_model_callbacks_selected = SetAllModelCallbacksSelected.Field()
