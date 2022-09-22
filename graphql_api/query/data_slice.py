from typing import List, Optional

import graphene

from controller.auth import manager as auth
from graphql_api.types import DataSlice
from controller.data_slice import manager


class DataSliceQuery(graphene.ObjectType):

    data_slices = graphene.Field(
        graphene.List(DataSlice),
        project_id=graphene.ID(required=True),
        slice_type=graphene.String(required=False),
    )

    static_data_slices_current_count = graphene.Field(
        graphene.Int,
        project_id=graphene.ID(required=True),
        slice_id=graphene.ID(required=True),
    )

    def resolve_data_slices(
        self, info, project_id: str, slice_type: Optional[str] = None
    ) -> List[DataSlice]:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_all_data_slices(project_id, slice_type)

    def resolve_static_data_slices_current_count(
        self, info, project_id: str, slice_id: str
    ) -> int:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.count_items(project_id, slice_id)
