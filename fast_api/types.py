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
        self.record_list = record_list if record_list is not None else []


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
        self.labels = labels if labels is not None else []


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
        self.labels = labels if labels is not None else []


class ZeroShotNRecordsWrapper:
    def __init__(
        self, duration: float = None, records: Optional[List[ZeroShotNRecords]] = None
    ):
        self.duration = duration
        self.records = records if records is not None else []


class ServiceVersionResult:
    def __init__(
        self,
        service: str = None,
        installed_version: str = None,
        remote_version: str = None,
        last_checked: datetime = None,
        remote_has_newer: bool = None,
        link: str = None,
    ):
        self.service = service
        self.installed_version = installed_version
        self.remote_version = remote_version
        self.last_checked = last_checked
        self.remote_has_newer = remote_has_newer
        self.link = link


class ModelProviderInfoResult:
    def __init__(
        self,
        name: str = None,
        revision: str = None,
        link: str = None,
        date: datetime = None,
        size: float = None,
        status: str = None,
        zero_shot_pipeline: bool = None,
    ):
        self.name = name
        self.revision = revision
        self.link = link
        self.date = date
        self.size = size
        self.status = status
        self.zero_shot_pipeline = zero_shot_pipeline


class HuddleData:
    def __init__(
        self,
        huddle_id: str = None,
        record_ids: List[str] = None,
        huddle_type: str = None,
        start_pos: int = None,
        allowed_task: str = None,
        can_edit: bool = None,
        checked_at: datetime = None,
    ):
        self.huddle_id = huddle_id
        self.record_ids = record_ids if record_ids is not None else []
        self.huddle_type = huddle_type
        self.start_pos = start_pos
        self.allowed_task = allowed_task
        self.can_edit = can_edit
        self.checked_at = checked_at


class LabelingFunctionSampleRecordWrapper:
    def __init__(
        self,
        record_id: str = None,
        calculated_labels: List[str] = None,
        full_record_data: str = None,
    ):
        self.record_id = record_id
        self.calculated_labels = (
            calculated_labels if calculated_labels is not None else []
        )
        self.full_record_data = full_record_data


class LabelingFunctionSampleRecords(graphene.ObjectType):
    records = graphene.List(LabelingFunctionSampleRecordWrapper)
    container_logs = graphene.List(graphene.String)
    code_has_errors = graphene.Boolean()


class GatesIntegrationData(graphene.ObjectType):
    status = graphene.String()
    missing_tokenizer = graphene.Boolean()
    missing_embeddings = graphene.List(graphene.String)
    missing_information_sources = graphene.List(graphene.String)
