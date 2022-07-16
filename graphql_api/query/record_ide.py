import graphene
from controller.auth import manager as auth
from controller.record_ide import manager


class RunRecordIDEPayload(graphene.ObjectType):
    run_record_ide = graphene.String(
        project_id=graphene.ID(required=True),
        record_id=graphene.ID(required=True),
        code=graphene.String(required=True),
    )

    def resolve_run_record_ide(self, info, project_id, record_id, code):
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_by_info(info).id
        return manager.create_record_ide_payload(
            user_id, project_id, record_id, code
        )
