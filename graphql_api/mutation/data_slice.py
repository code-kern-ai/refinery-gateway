from typing import Any, Dict, List, Optional

from controller.auth import manager as auth
from exceptions.exceptions import TooManyRecordsForStaticSliceException
import graphene
from graphql import GraphQLError

from submodules.model.business_objects import general
from submodules.model.enums import NotificationType
from util import notification
from controller.data_slice import manager


class CreateDataSlice(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        static = graphene.Boolean(required=True)
        filter_raw = graphene.JSONString(required=True)
        filter_data = graphene.List(graphene.JSONString, required=True)

    id = graphene.String()

    def mutate(
        self,
        info,
        project_id: str,
        name: str,
        static: bool,
        filter_raw: Dict[str, Any],
        filter_data: List[Dict[str, Any]],
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        try:
            data_slice_item = manager.create_data_slice(
                project_id, user.id, name, filter_raw, filter_data, static
            )
            notification.send_organization_update(
                project_id, f"data_slice_created:{str(data_slice_item.id)}"
            )
            return CreateDataSlice(id=data_slice_item.id)
        except Exception as e:
            handle_error(e, user.id, project_id)
            return GraphQLError(e)


class UpdateDataSlice(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        data_slice_id = graphene.ID(required=True)
        static = graphene.Boolean(required=True)
        filter_raw = graphene.JSONString(required=True)
        filter_data = graphene.List(graphene.JSONString)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        data_slice_id: str,
        static: bool,
        filter_raw: Dict[str, Any],
        filter_data: Optional[List[Dict[str, Any]]] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        try:
            manager.update_data_slice(
                project_id, data_slice_id, filter_data, filter_raw, static
            )
            notification.send_organization_update(
                project_id, f"data_slice_updated:{data_slice_id}"
            )
            return UpdateDataSlice(ok=True)
        except Exception as e:
            handle_error(e, user.id, project_id)
            return UpdateDataSlice(ok=False)


class DeleteDataSlice(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        data_slice_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, data_slice_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.delete_data_slice(project_id, data_slice_id)
        notification.send_organization_update(
            project_id, f"data_slice_deleted:{data_slice_id}"
        )
        return DeleteDataSlice(ok=True)


class CreateOutlierSlice(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        embedding_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id, embedding_id):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_id_by_info(info)
        data_slice_item = manager.create_outlier_slice(
            project_id, user_id, embedding_id
        )
        notification.send_organization_update(
            project_id, f"data_slice_created:{str(data_slice_item.id)}"
        )
        return CreateOutlierSlice(ok=True)


# update logic only to be run once
class UpdateSliceTypeManual(graphene.Mutation):
    class Arguments:
        execute = graphene.Boolean(required=False)

    ok = graphene.Boolean()

    def mutate(self, info, execute=False):
        auth.check_demo_access(info)
        if execute:
            manager.update_slice_type_manual_for_all()

        return UpdateSliceTypeManual(ok=True)


def handle_error(exception: Exception, user_id: str, project_id: str):
    general.rollback()
    if exception.__class__ == TooManyRecordsForStaticSliceException.__class__:
        error = "Too many records for a static slice"
    else:
        error = str(exception.__class__.__name__)

    notification.create_notification(
        NotificationType.DATA_SLICE_UPDATE_FAILED,
        user_id,
        project_id,
        error,
    )


class DataSliceMutation(graphene.ObjectType):
    create_data_slice = CreateDataSlice.Field()
    delete_data_slice = DeleteDataSlice.Field()
    update_data_slice = UpdateDataSlice.Field()
    create_outlier_slice = CreateOutlierSlice.Field()
    update_slice_type_manual = UpdateSliceTypeManual.Field()
