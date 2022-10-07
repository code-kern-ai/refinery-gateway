import graphene

from controller.auth import manager as auth
from graphql_api.types import InformationSourcePayload, LabelingFunctionSampleRecords
from controller.payload import manager


class PayloadQuery(graphene.ObjectType):

    payload_by_payload_id = graphene.Field(
        InformationSourcePayload,
        payload_id=graphene.ID(required=True),
        project_id=graphene.ID(required=True),
    )

    get_labeling_function_on_10_records = graphene.Field(
        LabelingFunctionSampleRecords,
        project_id=graphene.ID(required=True),
        information_source_id=graphene.ID(required=True),
    )

    def resolve_payload_by_payload_id(
        self, info, payload_id: str, project_id: str
    ) -> InformationSourcePayload:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_payload(project_id, payload_id)

    def resolve_get_labeling_function_on_10_records(
        self, info, project_id: str, information_source_id: str
    ) -> LabelingFunctionSampleRecords:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_labeling_function_on_10_records(
            project_id, information_source_id
        )
