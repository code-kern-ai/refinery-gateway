from typing import Any, Dict
import graphene
import json
import uuid

from controller.auth import manager as auth
from submodules.model.enums import InformationSourceType
from util import notification
from controller.record import manager as record_manager
from controller.embedding import manager as embedding_manager
from controller.project import manager as project_manager
from controller.payload import manager as payload_manager
from graphql_api import types


class DeleteRecord(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        record_id = graphene.ID()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, record_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.delete_record(project_id, record_id)
        notification.send_organization_update(project_id, f"record_deleted:{record_id}")
        return DeleteRecord(ok=True)


class RecordMutation(graphene.ObjectType):
    delete_record = DeleteRecord.Field()
