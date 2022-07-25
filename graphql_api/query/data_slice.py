from typing import List

import graphene

from controller.auth import manager as auth
from graphql_api.types import DataSlice
from controller.data_slice import manager


class DataSliceQuery(graphene.ObjectType):

    data_slices = graphene.Field(
        graphene.List(DataSlice),
        project_id=graphene.ID(required=True),
    )

    static_data_slices_current_count = graphene.Field(
        graphene.Int,
        project_id=graphene.ID(required=True),
        slice_id=graphene.ID(required=True),
    )

    def resolve_data_slices(self, info, project_id: str) -> List[DataSlice]:
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        return manager.get_all_data_slices(project_id)

    def resolve_static_data_slices_current_count(
        self, info, project_id: str, slice_id: str
    ) -> int:
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        return manager.count_items(project_id, slice_id)
