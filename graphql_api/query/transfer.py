from typing import Dict, List, Optional, Any

import graphene

from controller.auth import manager as auth
from controller.transfer import manager as transfer_manager, record_export_manager


class TransferQuery(graphene.ObjectType):

    upload_credentials_and_id = graphene.Field(
        graphene.JSONString,
        project_id=graphene.ID(required=True),
        file_name=graphene.String(required=True),
        file_type=graphene.String(required=True),
        file_import_options=graphene.String(required=False),
    )

    export = graphene.Field(
        graphene.JSONString,
        project_id=graphene.ID(required=True),
        session_id=graphene.ID(required=False),
    )

    export_project = graphene.Field(
        graphene.JSONString,
        project_id=graphene.ID(required=True),
        export_options=graphene.JSONString(required=False),
    )

    export_knowledge_base = graphene.Field(
        graphene.JSONString,
        project_id=graphene.ID(required=True),
        list_id=graphene.ID(required=True),
    )

    prepare_project_export = graphene.Field(
        graphene.Boolean,
        project_id=graphene.ID(required=True),
        export_options=graphene.JSONString(required=False),
    )

    last_record_export_credentials = graphene.Field(
        graphene.String,
        project_id=graphene.ID(required=True),
    )

    prepare_record_export = graphene.Field(
        graphene.Boolean,
        project_id=graphene.ID(required=True),
        export_options=graphene.JSONString(required=False),
    )

    labelstudio_template = graphene.Field(
        graphene.String,
        project_id=graphene.ID(required=True),
        labeling_task_ids=graphene.List(graphene.ID, required=True),
        attribute_ids=graphene.List(graphene.ID, required=True),
    )

    last_project_export_credentials = graphene.Field(
        graphene.String,
        project_id=graphene.ID(required=True),
    )

    def resolve_export_project(
        self, info, project_id: str, export_options: Optional[str] = None
    ) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_id_by_info(info)
        return transfer_manager.export_project(project_id, user_id, export_options)

    def resolve_upload_credentials_and_id(
        self,
        info,
        project_id: str,
        file_name: str,
        file_type: str,
        file_import_options: Optional[str] = "",
    ) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        return transfer_manager.get_upload_credentials_and_id(
            project_id, user.id, file_name, file_type, file_import_options
        )

    def resolve_export(
        self, info, project_id: str, session_id: Optional[str] = None
    ) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return transfer_manager.export_records(project_id, None, session_id)

    def resolve_export_knowledge_base(self, info, project_id: str, list_id: str) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return transfer_manager.export_knowledge_base(project_id, list_id)

    def resolve_prepare_project_export(
        self, info, project_id: str, export_options: Optional[str] = None
    ) -> bool:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_id_by_info(info)
        return transfer_manager.prepare_project_export(
            project_id, user_id, export_options
        )

    def resolve_last_project_export_credentials(self, info, project_id: str) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return transfer_manager.last_project_export_credentials(project_id)

    def resolve_prepare_record_export(
        self, info, project_id: str, export_options: Optional[Dict[str, Any]] = None
    ) -> bool:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_id_by_info(info)
        transfer_manager.prepare_record_export(project_id, user_id, export_options)
        return True

    def resolve_last_record_export_credentials(self, info, project_id: str) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_id_by_info(info)
        return transfer_manager.last_record_export_credentials(project_id, user_id)

    def resolve_labelstudio_template(
        self,
        info,
        project_id: str,
        labeling_task_ids: List[str],
        attribute_ids: List[str],
    ) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return transfer_manager.generate_labelstudio_template(
            project_id, labeling_task_ids, attribute_ids
        )
