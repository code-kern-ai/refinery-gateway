from typing import List, Optional

import graphene

from graphene_sqlalchemy.fields import SQLAlchemyConnectionField
from submodules.model.enums import LabelingTaskType
from graphql_api.types import (
    HuddleData,
    InterAnnotatorMatrix,
    ProjectSize,
    Project,
    UserSession,
)
from controller.auth import manager as auth
from controller.project import manager
from controller.labeling_task import manager as task_manager
from service.search import search
from util.inter_annotator.functions import (
    resolve_inter_annotator_matrix_classification,
    resolve_inter_annotator_matrix_extraction,
)


class ProjectQuery(graphene.ObjectType):
    project_by_project_id = graphene.Field(
        Project,
        project_id=graphene.ID(required=True),
    )

    project_size = graphene.Field(
        graphene.List(ProjectSize),
        project_id=graphene.ID(required=True),
    )

    all_projects = SQLAlchemyConnectionField(Project.connection)

    user_session_by_session_id = graphene.Field(
        UserSession,
        project_id=graphene.ID(required=True),
        session_id=graphene.ID(required=True),
    )

    inter_annotator_matrix = graphene.Field(
        InterAnnotatorMatrix,
        project_id=graphene.ID(required=True),
        labeling_task_id=graphene.ID(required=True),
        include_gold_star=graphene.Boolean(required=False),
        include_all_org_user=graphene.Boolean(required=False),
        only_on_static_slice=graphene.ID(required=False),
    )

    general_project_stats = graphene.Field(
        graphene.JSONString,
        project_id=graphene.ID(required=True),
        labeling_task_id=graphene.ID(required=False),
        slice_id=graphene.ID(required=False),
    )
    label_distribution = graphene.Field(
        graphene.JSONString,
        project_id=graphene.ID(required=True),
        labeling_task_id=graphene.ID(required=False),
        slice_id=graphene.ID(required=False),
    )

    confusion_matrix = graphene.Field(
        graphene.JSONString,
        project_id=graphene.ID(required=True),
        labeling_task_id=graphene.ID(required=True),
        slice_id=graphene.ID(required=False),
    )

    is_rats_tokenization_still_running = graphene.Field(
        graphene.Boolean,
        project_id=graphene.ID(required=True),
    )

    request_huddle_data = graphene.Field(
        HuddleData,
        project_id=graphene.ID(required=True),
        huddle_id=graphene.ID(required=True),
        huddle_type=graphene.String(required=True),
    )

    def resolve_project_by_project_id(self, info, project_id: str) -> Project:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_project(project_id)

    def resolve_project_size(self, info, project_id: str) -> List[ProjectSize]:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_project_size(project_id)

    def resolve_all_projects(self, info, sort) -> List[Project]:
        auth.check_demo_access(info)
        organization = auth.get_organization_id_by_info(info)
        return manager.get_all_projects(organization.id)

    def resolve_user_session_by_session_id(
        self, info, project_id: str, session_id: str
    ) -> UserSession:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_by_info(info).id
        return search.resolve_labeling_session(project_id, user_id, session_id)

    def resolve_inter_annotator_matrix(
        self,
        info,
        project_id: str,
        labeling_task_id: str,
        include_gold_star: Optional[bool] = True,
        include_all_org_user: Optional[bool] = False,
        only_on_static_slice: Optional[str] = None,
    ) -> InterAnnotatorMatrix:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        labeling_task = task_manager.get_labeling_task(project_id, labeling_task_id)
        if not labeling_task:
            raise ValueError("Can't match labeling task to given Ids")

        if labeling_task.task_type == LabelingTaskType.CLASSIFICATION.value:
            return resolve_inter_annotator_matrix_classification(
                labeling_task,
                include_gold_star,
                include_all_org_user,
                only_on_static_slice,
            )
        elif labeling_task.task_type == LabelingTaskType.INFORMATION_EXTRACTION.value:
            return resolve_inter_annotator_matrix_extraction(
                labeling_task,
                include_gold_star,
                include_all_org_user,
                only_on_static_slice,
            )

        raise ValueError(f"Can't match task type {labeling_task.task_type}")

    def resolve_general_project_stats(
        self,
        info,
        project_id: str,
        labeling_task_id: Optional[str] = None,
        slice_id: Optional[str] = None,
    ) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_general_project_stats(project_id, labeling_task_id, slice_id)

    def resolve_label_distribution(
        self,
        info,
        project_id: str,
        labeling_task_id: Optional[str] = None,
        slice_id: Optional[str] = None,
    ) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_label_distribution(project_id, labeling_task_id, slice_id)

    def resolve_confusion_matrix(
        self,
        info,
        project_id: str,
        labeling_task_id: str,
        slice_id: Optional[str] = None,
    ) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_confusion_matrix(project_id, labeling_task_id, slice_id)

    def resolve_is_rats_tokenization_still_running(self, info, project_id) -> bool:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.is_rats_tokenization_still_running(project_id)

    def resolve_request_huddle_data(
        self, info, project_id: str, huddle_id: str, huddle_type: str
    ) -> HuddleData:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_by_info(info).id
        return manager.resolve_request_huddle_data(
            project_id, user_id, huddle_id, huddle_type
        )
