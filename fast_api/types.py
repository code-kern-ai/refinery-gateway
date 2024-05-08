import json
import datetime
import decimal
from typing import List, Optional
from uuid import UUID
import graphene


class ExtendedRecord:
    def __init__(self, **fields):
        self._fields = fields

    def get_record_data(self):
        def alchemy_encoder(obj):
            """Custom JSON encoder function for SQLAlchemy special types."""
            if isinstance(obj, datetime.date):
                return obj.isoformat()
            elif isinstance(obj, decimal.Decimal):
                return float(obj)
            elif isinstance(obj, UUID):
                return str(obj)

        # Serializes the attributes in _fields using the custom encoder
        return json.dumps(
            {key: getattr(self, key) for key in self._fields}, default=alchemy_encoder
        )


class ExtendedSearch:
    def __init__(
        self,
        sql: str = None,
        query_limit: int = None,
        query_offset: int = None,
        full_count: int = None,
        session_id: UUID = None,
        record_list: Optional[List[ExtendedRecord]] = None,
    ):
        self.sql = sql
        self.query_limit = query_limit
        self.query_offset = query_offset
        self.full_count = full_count
        self.session_id = session_id
        self.record_list = record_list


class ToolTip:
    def __init__(
        self,
        key: str = None,
        title: str = None,
        text: str = None,
        href: str = None,
        href_caption: str = None,
    ):
        self.key = key
        self.title = title
        self.text = text
        self.href = href
        self.href_caption = href_caption


class ProjectSize:
    def __init__(
        self,
        order: int = None,
        table: str = None,
        description: str = None,
        default: bool = None,
        byte_size: float = None,
        byte_readable: str = None,
    ):
        self.order = order
        self.table = table
        self.description = description
        self.default = default
        self.byte_size = byte_size
        self.byte_readable = byte_readable


class LabelConfidenceWrapper:
    def __init__(self, label_name: str = None, confidence: float = None):
        self.label_name = label_name
        self.confidence = confidence


class ZeroShotTextResult:
    def __init__(
        self,
        config: str = None,
        text: str = None,
        labels: Optional[List[LabelConfidenceWrapper]] = None,
    ):
        self.config = config
        self.text = text
        self.labels = labels


class ZeroShotNRecords:
    def __init__(
        self,
        record_id: str = None,
        checked_text: str = None,
        full_record_data: json = None,
        labels: Optional[List[LabelConfidenceWrapper]] = None,
    ):
        self.record_id = record_id
        self.checked_text = checked_text
        self.full_record_data = full_record_data
        self.labels = labels


# TODO
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
