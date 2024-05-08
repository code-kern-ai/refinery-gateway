import json
import datetime
import decimal
from uuid import UUID
import graphene
from graphene.relay import Node
from graphene_sqlalchemy.types import SQLAlchemyObjectType
from submodules.model.business_objects import (
    task_queue,
)
from submodules.model import models
from controller.auth import kratos


class User(SQLAlchemyObjectType):
    class Meta:
        model = models.User
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)
    mail = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()

    def resolve_mail(self, info) -> str:
        return kratos.resolve_user_mail_by_id(self.id)

    def resolve_first_name(self, info):
        user = kratos.resolve_user_name_by_id(self.id)
        if user:
            return user["first"]
        return None

    def resolve_last_name(self, info):
        user = kratos.resolve_user_name_by_id(self.id)
        if user:
            return user["last"]
        return None


class Attribute(SQLAlchemyObjectType):
    class Meta:
        model = models.Attribute
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)
    state = graphene.String()

    def resolve_state(self, info):
        waiting_attribute = task_queue.get_waiting_by_attribute_id(
            self.project_id, str(self.id)
        )
        if waiting_attribute:
            return "QUEUED"
        return self.state


class InterAnnotatorElement(graphene.ObjectType):
    user_id_a = graphene.String()
    user_id_b = graphene.String()
    percent = graphene.Float()


class UserCountWrapper(graphene.ObjectType):
    user = graphene.Field(User)
    count = graphene.Int()


class UserCountsWrapper(graphene.ObjectType):
    user = graphene.Field(User)
    counts = graphene.JSONString()


class InterAnnotatorMatrix(graphene.ObjectType):
    all_users = graphene.List(UserCountWrapper)
    count_names = graphene.Int()
    elements = graphene.List(InterAnnotatorElement)


class TokenWrapper(graphene.ObjectType):
    value = graphene.String()
    idx = graphene.Int()
    pos_start = graphene.Int()
    pos_end = graphene.Int()
    type = graphene.String()


class TokenizedAttribute(graphene.ObjectType):
    raw = graphene.String()
    attribute = graphene.Field(Attribute)
    tokens = graphene.List(TokenWrapper)


class TokenizedRecord(graphene.ObjectType):
    record_id = graphene.UUID()
    attributes = graphene.List(TokenizedAttribute)


class ExtendedRecord(graphene.ObjectType):
    record_data = graphene.String()

    def resolve_record_data(self, info):
        def alchemy_encoder(obj):
            if isinstance(obj, datetime.date):
                return obj.isoformat()
            elif isinstance(obj, decimal.Decimal):
                return float(obj)
            elif isinstance(obj, UUID):
                return str(obj)

        return json.dumps(
            {c: getattr(self, c) for c in self._fields},
            default=alchemy_encoder,
        )


class ExtendedSearch(graphene.ObjectType):
    sql = graphene.String()
    query_limit = graphene.Int()
    query_offset = graphene.Int()
    full_count = graphene.Int()
    session_id = graphene.UUID()
    record_list = graphene.List(ExtendedRecord)


class ToolTip(graphene.ObjectType):
    key = graphene.String()
    title = graphene.String()
    text = graphene.String()
    href = graphene.String()
    href_caption = graphene.String()


class ProjectSize(graphene.ObjectType):
    order = graphene.Int()
    table = graphene.String()
    description = graphene.String()
    default = graphene.Boolean()
    byte_size = graphene.Float()  # int is to small therfore as float
    byte_readable = graphene.String()


class LabelConfidenceWrapper(graphene.ObjectType):
    label_name = graphene.String()
    confidence = graphene.Float()


class ZeroShotTextResult(graphene.ObjectType):
    config = graphene.String()
    text = graphene.String()
    labels = graphene.List(LabelConfidenceWrapper)


class ZeroShotNRecords(graphene.ObjectType):
    record_id = graphene.ID()
    checked_text = graphene.String()
    full_record_data = graphene.JSONString()
    labels = graphene.List(LabelConfidenceWrapper)


class ZeroShotNRecordsWrapper(graphene.ObjectType):
    duration = graphene.Float()
    records = graphene.List(ZeroShotNRecords)


class ServiceVersionResult(graphene.ObjectType):
    service = graphene.String()
    installed_version = graphene.String()
    remote_version = graphene.String()
    last_checked = graphene.DateTime()
    remote_has_newer = graphene.Boolean()
    link = graphene.String()


class ModelProviderInfoResult(graphene.ObjectType):
    name = graphene.String()
    revision = graphene.String()
    link = graphene.String()
    date = graphene.DateTime()
    size = graphene.Float()  # int is to small therfore as float
    status = graphene.String()
    zero_shot_pipeline = graphene.Boolean()


class HuddleData(graphene.ObjectType):
    huddle_id = graphene.ID()
    record_ids = graphene.List(graphene.ID)
    huddle_type = graphene.String()
    # usually 0 if first unlabled is requested then the position of that
    start_pos = graphene.Int()
    # only filled if nessecary
    allowed_task = graphene.String()
    can_edit = graphene.Boolean()
    checked_at = graphene.DateTime()


class LabelingFunctionSampleRecordWrapper(graphene.ObjectType):
    record_id = graphene.ID()
    calculated_labels = graphene.List(graphene.String)
    full_record_data = graphene.JSONString()


class LabelingFunctionSampleRecords(graphene.ObjectType):
    records = graphene.List(LabelingFunctionSampleRecordWrapper)
    container_logs = graphene.List(graphene.String)
    code_has_errors = graphene.Boolean()


class GatesIntegrationData(graphene.ObjectType):
    status = graphene.String()
    missing_tokenizer = graphene.Boolean()
    missing_embeddings = graphene.List(graphene.String)
    missing_information_sources = graphene.List(graphene.String)
