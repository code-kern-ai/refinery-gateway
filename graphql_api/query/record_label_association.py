from typing import List

import graphene

from controller.auth import manager as auth
from controller.record_label_association import manager
from graphql_api.types import RecordLabelAssociation


class RecordLabelAssociationQuery(graphene.ObjectType):
    last_annotated_records = graphene.Field(
        graphene.List(RecordLabelAssociation),
        project_id=graphene.ID(required=True),
        top_n=graphene.Int(required=True),
    )

    def resolve_last_annotated_records(
        self, info, project_id: str, top_n: int
    ) -> List[RecordLabelAssociation]:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_last_annotated_record_id(project_id, top_n)
