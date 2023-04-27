import graphene
from graphql_api.mutation.admin_message import AdminMessageMutation
from graphql_api.mutation.monitor import MonitorMutation

from graphql_api.mutation.upload_task import UploadTaskMutation
from graphql_api.query.admin_message import AdminMessageQuery
from graphql_api.query.attribute import AttributeQuery
from graphql_api.query.comment import CommentQuery
from graphql_api.query.data_slice import DataSliceQuery
from graphql_api.query.labeling_access_link import LabelingAccessLinkQuery
from graphql_api.query.embedding import EmbeddingQuery
from graphql_api.query.monitor import MonitorQuery
from graphql_api.query.personal_access_token import PersonalAccessTokenQuery
from graphql_api.query.transfer import TransferQuery
from graphql_api.query.information_source import InformationSourceQuery
from graphql_api.query.knowledge_base import KnowledgeBaseQuery
from graphql_api.query.knowledge_term import KnowledgeTermQuery
from graphql_api.query.labeling_task import LabelingTaskQuery
from graphql_api.query.labeling_task_label import LabelingTaskLabelQuery
from graphql_api.query.misc import MiscQuery
from graphql_api.query.notification import NotificationQuery
from graphql_api.query.organization import OrganizationQuery
from graphql_api.query.payload import PayloadQuery
from graphql_api.query.project import ProjectQuery
from graphql_api.query.record import RecordQuery
from graphql_api.query.task_queue import TaskQueueQuery
from graphql_api.query.record_label_association import RecordLabelAssociationQuery
from graphql_api.query.user import UserQuery
from graphql_api.query.zero_shot import ZeroShotQuery
from graphql_api.query.upload_task import UploadTaskQuery
from graphql_api.query.weak_supervision import WeakSupervisionQuery
from graphql_api.query.record_ide import RunRecordIDEPayload
from graphql_api.query.model_provider import ModelProviderQuery

from graphql_api.mutation.attribute import AttributeMutation
from graphql_api.mutation.misc import MiscMutation
from graphql_api.mutation.comment import CommentMutation
from graphql_api.mutation.data_slice import DataSliceMutation
from graphql_api.mutation.labeling_access_link import LabelingAccessLinkMutation
from graphql_api.mutation.embedding import EmbeddingMutation
from graphql_api.mutation.information_source import InformationSourceMutation
from graphql_api.mutation.knowledge_base import KnowledgeBaseMutation
from graphql_api.mutation.knowledge_term import KnowledgeTermMutation
from graphql_api.mutation.labeling_task import LabelingTaskMutation
from graphql_api.mutation.labeling_task_label import LabelingTaskLabelMutation
from graphql_api.mutation.model_provider import ModelProviderMutation
from graphql_api.mutation.notification import NotificationMutation
from graphql_api.mutation.organization import OrganizationMutation
from graphql_api.mutation.payload import PayloadMutation
from graphql_api.mutation.project import ProjectMutation
from graphql_api.mutation.record import RecordMutation
from graphql_api.mutation.task_queue import TaskQueueMutation
from graphql_api.mutation.record_label_association import RecordLabelAssociationMutation
from graphql_api.mutation.tokenization import TokenizationMutation
from graphql_api.mutation.weak_supervisor import WeakSupervisionMutation
from graphql_api.mutation.zero_shot import ZeroShotMutation
from graphql_api.mutation.personal_access_token import PersonalAccessTokenMutation


class Query(
    AttributeQuery,
    CommentQuery,
    DataSliceQuery,
    LabelingAccessLinkQuery,
    EmbeddingQuery,
    TransferQuery,
    InformationSourceQuery,
    KnowledgeBaseQuery,
    KnowledgeTermQuery,
    LabelingTaskQuery,
    LabelingTaskLabelQuery,
    MiscQuery,
    ModelProviderQuery,
    OrganizationQuery,
    PayloadQuery,
    ProjectQuery,
    RecordLabelAssociationQuery,
    RecordQuery,
    TaskQueueQuery,
    NotificationQuery,
    UploadTaskQuery,
    WeakSupervisionQuery,
    ZeroShotQuery,
    RunRecordIDEPayload,
    PersonalAccessTokenQuery,
    AdminMessageQuery,
    UserQuery,
    MonitorQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    AttributeMutation,
    CommentMutation,
    DataSliceMutation,
    LabelingAccessLinkMutation,
    EmbeddingMutation,
    InformationSourceMutation,
    KnowledgeBaseMutation,
    KnowledgeTermMutation,
    MiscMutation,
    ModelProviderMutation,
    LabelingTaskLabelMutation,
    LabelingTaskMutation,
    NotificationMutation,
    OrganizationMutation,
    PayloadMutation,
    ProjectMutation,
    RecordLabelAssociationMutation,
    RecordMutation,
    TaskQueueMutation,
    TokenizationMutation,
    WeakSupervisionMutation,
    ZeroShotMutation,
    UploadTaskMutation,
    PersonalAccessTokenMutation,
    AdminMessageMutation,
    MonitorMutation,
    graphene.ObjectType,
):
    pass
