import graphene
from typing import Dict, Any

from controller.auth import manager as auth
from util import notification
from controller.record import manager


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


class EditRecords(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        changes = graphene.JSONString()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, changes: Dict[str,Any]):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.edit_records(project_id, changes)

        # somewhat global atm since record specific might result in a lot of notifications
        notification.send_organization_update(project_id, f"records_changed")
        return DeleteRecord(ok=True)


class RecordMutation(graphene.ObjectType):
    delete_record = DeleteRecord.Field()
    edit_records = EditRecords.Field()
