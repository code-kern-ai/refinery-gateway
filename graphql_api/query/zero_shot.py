from typing import List, Optional, Dict

from graphql_api import types
from controller.auth import manager as auth_manager
import graphene

from controller.zero_shot import manager
from graphql_api.types import ZeroShotNRecordsWrapper, ZeroShotTextResult


class ZeroShotQuery(graphene.ObjectType):

    zero_shot_text = graphene.Field(
        ZeroShotTextResult,
        project_id=graphene.ID(required=True),
        information_source_id=graphene.ID(required=True),
        config=graphene.String(required=True),
        text=graphene.String(required=True),
        run_individually=graphene.Boolean(required=True),
        label_names=graphene.JSONString(required=True),
    )

    zero_shot_recommendations = graphene.Field(
        graphene.JSONString,
        project_id=graphene.ID(required=False),
    )

    zero_shot_10_records = graphene.Field(
        ZeroShotNRecordsWrapper,
        project_id=graphene.ID(required=True),
        information_source_id=graphene.ID(required=True),
        label_names=graphene.JSONString(),
    )

    # resolver -------------------------------------------------------------------------

    def resolve_zero_shot_text(
        self,
        info,
        project_id: str,
        information_source_id: str,
        config: str,
        text: str,
        run_individually: bool,
        label_names: List[str],
    ) -> ZeroShotTextResult:
        auth_manager.check_demo_access(info)
        return manager.get_zero_shot_text(
            project_id,
            information_source_id,
            config,
            text,
            run_individually,
            label_names,
        )

    def resolve_zero_shot_recommendations(
        self, info, project_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        auth_manager.check_demo_access(info)
        if project_id:
            auth_manager.check_project_access(info, project_id)
        return manager.get_zero_shot_recommendations(project_id)

    def resolve_zero_shot_10_records(
        self,
        info,
        project_id: str,
        information_source_id: str,
        label_names: List[str] = None,
    ) -> ZeroShotNRecordsWrapper:
        auth_manager.check_demo_access(info)
        auth_manager.check_project_access(info, project_id)
        return manager.get_zero_shot_10_records(
            project_id,
            information_source_id,
            label_names,
        )
