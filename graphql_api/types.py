import json
import datetime
import decimal
from uuid import UUID
import graphene
from graphene.relay import Node
from graphene.types.generic import GenericScalar
from graphene_sqlalchemy.types import SQLAlchemyObjectType
from submodules.model import enums
from submodules.model.business_objects import (
    data_slice,
    knowledge_term,
    record_label_association,
    embedding,
    record,
    attribute,
    information_source,
    labeling_task,
    project,
    task_queue,
)
from submodules.model import models
from util import notification
from controller.auth import kratos
from util.inter_annotator.functions import (
    resolve_inter_annotator_matrix_classification,
    resolve_inter_annotator_matrix_extraction,
)


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


class Label(SQLAlchemyObjectType):
    class Meta:
        model = models.LabelingTaskLabel
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)

    # TODO: can these now be removed?
    num_data_scale_manual = graphene.Int()
    ratio_data_scale_manual = graphene.Float()

    num_data_test_manual = graphene.Int()
    ratio_data_test_manual = graphene.Float()

    num_data_scale_programmatic = graphene.Int()
    ratio_data_scale_programmatic = graphene.Float()

    @staticmethod
    def _count_absolute(record_category, label_source, self):
        return record_label_association.count_absolute(
            self.id, record_category, label_source
        )

    @staticmethod
    def _count_relative(record_category, label_source, self):
        count_all_labels_in_task = record_label_association.count_relative(
            self.labeling_task_id, record_category, label_source
        )

        if count_all_labels_in_task == 0:
            return 0
        else:
            return (
                Label._count_absolute(record_category, label_source, self)
                / count_all_labels_in_task
            )

    def resolve_num_data_scale_manual(self, info):
        return Label._count_absolute(
            enums.RecordCategory.SCALE.value, enums.LabelSource.MANUAL.value, self
        )

    def resolve_num_data_test_manual(self, info):
        return Label._count_absolute(
            enums.RecordCategory.TEST.value, enums.LabelSource.MANUAL.value, self
        )

    def resolve_num_data_scale_programmatic(self, info):
        return Label._count_absolute(
            enums.RecordCategory.SCALE.value,
            enums.LabelSource.WEAK_SUPERVISION.value,
            self,
        )

    def resolve_ratio_data_scale_manual(self, info):
        return Label._count_relative(
            enums.RecordCategory.SCALE.value, enums.LabelSource.MANUAL.value, self
        )

    def resolve_ratio_data_test_manual(self, info):
        return Label._count_relative(
            enums.RecordCategory.TEST.value, enums.LabelSource.MANUAL.value, self
        )

    def resolve_ratio_data_scale_programmatic(self, info):
        return Label._count_relative(
            enums.RecordCategory.SCALE.value,
            enums.LabelSource.WEAK_SUPERVISION.value,
            self,
        )


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


class Embedding(SQLAlchemyObjectType):
    class Meta:
        model = models.Embedding
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)
    dimension = graphene.Int()
    count = graphene.Int()
    progress = graphene.Float()

    def resolve_count(self, info):
        return embedding.get_tensor_count(self.id)

    def resolve_dimension(self, info):
        embedding_item = embedding.get_tensor(self.id)

        if embedding_item is not None:
            # distinguish between token and attribute embeddings
            if type(embedding_item.data[0]) is list:
                return len(embedding_item.data[0])
            else:
                return len(embedding_item.data)
        else:
            return 0

    def resolve_progress(self, info):
        if self.state == "FINISHED":
            return 1
        num_records = len(self.project.records)  # can never be 0
        progress = 0.1 if self.state != "INITIALIZING" else 0
        return min(
            progress + (Embedding.resolve_count(self, info) / num_records * 0.9), 0.99
        )


class Project(SQLAlchemyObjectType):
    class Meta:
        model = models.Project
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)
    num_data_scale_manual = graphene.Int()
    num_data_scale_programmatical = graphene.Int()
    num_data_test_manual = graphene.Int()
    num_data_test_uploaded = graphene.Int()
    num_data_scale_uploaded = graphene.Int()
    contains_unique_attribute = graphene.Boolean()
    project_type = graphene.String()

    @staticmethod
    def _count_records(record_category, label_source, self):
        return record.count_by_project_and_source(
            self.id, record_category, label_source
        )

    def resolve_num_data_scale_manual(self, info):
        if self.status == enums.ProjectStatus.IN_DELETION.value:
            return -1

        return Project._count_records(
            enums.RecordCategory.SCALE.value, enums.LabelSource.MANUAL.value, self
        )

    def resolve_num_data_scale_programmatical(self, info):
        if self.status == enums.ProjectStatus.IN_DELETION.value:
            return -1

        return Project._count_records(
            enums.RecordCategory.SCALE.value,
            enums.LabelSource.WEAK_SUPERVISION.value,
            self,
        )

    def resolve_num_data_test_manual(self, info):
        if self.status == enums.ProjectStatus.IN_DELETION.value:
            return -1

        return Project._count_records(
            enums.RecordCategory.TEST.value, enums.LabelSource.MANUAL.value, self
        )

    def resolve_num_data_scale_uploaded(self, info):
        if self.status == enums.ProjectStatus.IN_DELETION.value:
            return -1

        return record.get_count_scale_uploaded(self.id)

    def resolve_num_data_test_uploaded(self, info):
        if self.status == enums.ProjectStatus.IN_DELETION.value:
            return -1

        return record.get_count_test_uploaded(self.id)

    def resolve_contains_unique_attribute(self, info):
        return attribute.get_unique_attributes_count(self.id) > 0


class RecordInput(graphene.InputObjectType):
    data = GenericScalar()


class InformationSourcePayload(SQLAlchemyObjectType):
    class Meta:
        model = models.InformationSourcePayload
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


class SourceStatistics(SQLAlchemyObjectType):
    class Meta:
        model = models.InformationSourceStatistics
        interfaces = (Node,)

    active = graphene.Boolean()

    def resolve_active(self, info):
        return information_source.check_is_active(self.project_id, self.id)

    id = graphene.ID(source="id", required=True)


class ConfusionMatrixElement(graphene.ObjectType):
    labelNameManual = graphene.String()
    labelNameProgrammatic = graphene.String()
    counts = graphene.Float()


class LabelDistribution(graphene.ObjectType):
    labelId = graphene.ID(required=True)
    ratioTestManually = graphene.Float()
    ratioScaleManually = graphene.Float()
    ratioScaleProgrammatically = graphene.Float()


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


class LabelingTask(SQLAlchemyObjectType):
    class Meta:
        model = models.LabelingTask
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)
    # TODO: can these now be removed ?
    confusion_matrix = graphene.Field(graphene.List(ConfusionMatrixElement))
    inter_annotator_matrix = graphene.Field(InterAnnotatorMatrix)
    confidence_distribution = graphene.JSONString()

    @staticmethod
    def _resolve_record_classifications(label_id, label_source, self):
        if label_source == enums.LabelSource.MANUAL.value:
            return labeling_task.get_record_classifications_manual(
                self.project_id, str(self.id), label_id
            )

        else:
            return labeling_task.get_record_classifications(
                self.project_id, label_id, label_source
            )

    @staticmethod
    def _get_relevant_extraction_records(self):
        return labeling_task.get_relevant_extraction_records(self.project_id, self.id)

    @staticmethod
    def _resolve_record_extraction_vector_triplets_manual(record_id, self):
        return labeling_task.get_record_extraction_vector_triplets_manual(
            self.project_id, self.id, record_id
        )

    @staticmethod
    def _resolve_record_extraction_vector_triplets_weak_supervision(record_id, self):
        return labeling_task.get_record_extraction_vector_triplets_weak_supervision(
            record_id, self.id
        )

    @staticmethod
    def _resolve_record_extraction_vector(record_id, label_source, self):
        if label_source == enums.LabelSource.MANUAL.value:
            triplets = LabelingTask._resolve_record_extraction_vector_triplets_manual(
                record_id, self
            )
        else:
            triplets = LabelingTask._resolve_record_extraction_vector_triplets_weak_supervision(
                record_id, self
            )

        if len(triplets) == 0:
            return None
        vector_len = triplets[0][2]
        vector = [
            enums.ConfusionMatrixElements.OUTSIDE.value for _ in range(vector_len)
        ]
        for label_name, token_index, _ in triplets:
            vector[token_index] = label_name
        return vector

    def resolve_confusion_matrix(self, info):
        confusion_matrix = []
        if self.task_type == enums.LabelingTaskType.CLASSIFICATION.value:
            for label_truth in self.labels:
                record_hits_truth = LabelingTask._resolve_record_classifications(
                    label_truth.id, enums.LabelSource.MANUAL.value, self
                )
                for label_prediction in self.labels:
                    record_hits_prediction = (
                        LabelingTask._resolve_record_classifications(
                            label_prediction.id,
                            enums.LabelSource.WEAK_SUPERVISION.value,
                            self,
                        )
                    )
                    count = len(record_hits_truth.intersection(record_hits_prediction))
                    confusion_matrix.append(
                        ConfusionMatrixElement(
                            label_truth.name, label_prediction.name, count
                        )
                    )
        elif self.task_type == enums.LabelingTaskType.INFORMATION_EXTRACTION.value:
            confusion_matrix_elements = {}
            for label_gt in self.labels + [
                Label(name=enums.ConfusionMatrixElements.OUTSIDE.value)
            ]:
                confusion_matrix_elements[label_gt.name] = {}
                for label_pred in self.labels + [
                    Label(name=enums.ConfusionMatrixElements.OUTSIDE.value)
                ]:
                    confusion_matrix_elements[label_gt.name][label_pred.name] = 0
            record_ids = LabelingTask._get_relevant_extraction_records(self)
            any_programmatic = False
            for (record_id,) in record_ids:
                vector_manual = LabelingTask._resolve_record_extraction_vector(
                    record_id, enums.LabelSource.MANUAL.value, self
                )
                if not vector_manual:
                    continue
                vector_programmatic = LabelingTask._resolve_record_extraction_vector(
                    record_id, enums.LabelSource.WEAK_SUPERVISION.value, self
                )
                if vector_programmatic is not None:
                    any_programmatic = True
                else:
                    vector_programmatic = [
                        enums.ConfusionMatrixElements.OUTSIDE.value
                        for _ in range(len(vector_manual))
                    ]
                for label_gt, label_pred in zip(vector_manual, vector_programmatic):
                    confusion_matrix_elements[label_gt][label_pred] += 1

            for label_gt, label_pred_dict in confusion_matrix_elements.items():
                for label_pred, count in label_pred_dict.items():
                    if not any_programmatic:
                        count = 0
                    confusion_matrix.append(
                        ConfusionMatrixElement(label_gt, label_pred, count)
                    )
        return confusion_matrix

    def resolve_inter_annotator_matrix(self, info):
        # use schema function for accessible variables
        if self.task_type == enums.LabelingTaskType.CLASSIFICATION.value:
            return resolve_inter_annotator_matrix_classification(
                self, True, False, None
            )
        elif self.task_type == enums.LabelingTaskType.INFORMATION_EXTRACTION.value:
            return resolve_inter_annotator_matrix_extraction(self, True, False, None)

        raise ValueError(f"Can't match task type {self.task_type}")

    def resolve_confidence_distribution(self, info):
        confidence_scores = project.get_confidence_distribution(
            self.project_id, self.id, num_samples=100
        )
        return confidence_scores


class InformationSource(SQLAlchemyObjectType):
    class Meta:
        model = models.InformationSource
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)
    last_payload = graphene.Field(InformationSourcePayload)

    def resolve_last_payload(self, info):
        ##check queued stuff
        waiting_payload = task_queue.get_waiting_by_information_source(
            self.project_id, str(self.id)
        )
        if waiting_payload:
            return InformationSourcePayload(
                id=waiting_payload.id,
                created_at=waiting_payload.created_at,
                state="QUEUED",
                iteration=-1,
                progress=0,
            )
        return information_source.get_last_payload(self.project_id, self.id)


class Organization(SQLAlchemyObjectType):
    class Meta:
        model = models.Organization
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


class Tensor(SQLAlchemyObjectType):
    class Meta:
        model = models.EmbeddingTensor
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


class RecordLabelAssociation(SQLAlchemyObjectType):
    class Meta:
        model = models.RecordLabelAssociation
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)
    token_start_idx = graphene.Int()
    token_end_idx = graphene.Int()
    comment = graphene.String()

    def resolve_token_start_idx(self, info):
        if len(self.tokens) > 0:
            return self.tokens[0].token_index

    def resolve_token_end_idx(self, info):
        if len(self.tokens) > 0:
            return self.tokens[-1].token_index

    def resolve_comment(self, info):
        return "DUMMY_FROM_RESOLVER"


class Record(SQLAlchemyObjectType):
    class Meta:
        model = models.Record
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


class DataSlice(SQLAlchemyObjectType):
    class Meta:
        model = models.DataSlice
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


class LabelingAccessLink(SQLAlchemyObjectType):
    class Meta:
        model = models.LabelingAccessLink
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)
    name = graphene.String()

    def resolve_name(self, info):
        if self.link_type == enums.LinkTypes.HEURISTIC.value:
            return information_source.get(self.project_id, self.heuristic_id).name
        elif self.link_type == enums.LinkTypes.DATA_SLICE.value:
            return data_slice.get(self.project_id, self.data_slice_id).name
        return "Unknown type"


class Notification(SQLAlchemyObjectType):
    class Meta:
        model = models.Notification
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)
    title = graphene.String()
    page = graphene.String()
    docs = graphene.String()

    def resolve_title(self, info):
        return notification.get_notification_data(self.type).get(
            "title",
        )

    def resolve_page(self, info):
        return notification.get_notification_data(self.type).get(
            "page",
        )

    def resolve_docs(self, info):
        return notification.get_notification_data(self.type).get(
            "docs",
        )


class PersonalAccessToken(graphene.ObjectType):
    id = graphene.ID()
    project_id = graphene.ID()
    name = graphene.String()
    scope = graphene.String()
    created_by = graphene.String()
    created_at = graphene.DateTime()
    expires_at = graphene.DateTime()
    last_used = graphene.DateTime()

    def resolve_created_by(self, info):
        name = kratos.resolve_user_name_by_id(self.user_id)
        return f"{name.get('first')} {name.get('last')}"


class KnowledgeBase(SQLAlchemyObjectType):
    class Meta:
        model = models.KnowledgeBase
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)
    name_as_variable = graphene.String()
    term_count = graphene.Int()

    def resolve_name_as_variable(self, info):
        return self.name.lower().replace(" ", "_")

    def resolve_term_count(self, info):
        return knowledge_term.count(self.project_id, self.id)


class Term(SQLAlchemyObjectType):
    class Meta:
        model = models.KnowledgeTerm
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


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


# SpaCy Tokenizer
class LanguageModel(graphene.ObjectType):
    name = graphene.String()
    config_string = graphene.String()


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


# Huggingface Encoder
class Encoder(graphene.ObjectType):
    config_string = graphene.String()
    description = graphene.String()
    tokenizers = graphene.List(graphene.String)
    applicability = graphene.JSONString()


class UploadTask(SQLAlchemyObjectType):
    class Meta:
        model = models.UploadTask
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


class UserSession(SQLAlchemyObjectType):
    class Meta:
        model = models.UserSessions
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


class ProjectSize(graphene.ObjectType):
    order = graphene.Int()
    table = graphene.String()
    description = graphene.String()
    default = graphene.Boolean()
    byte_size = graphene.Float()  # int is to small therfore as float
    byte_readable = graphene.String()


class UserActivity(SQLAlchemyObjectType):
    class Meta:
        model = models.UserActivity
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


class UserActivityWrapper(graphene.ObjectType):
    user = graphene.Field(User)
    user_activity = graphene.List(graphene.JSONString)
    warning = graphene.Boolean()
    warning_text = graphene.String()


class WeakSupervisionTask(SQLAlchemyObjectType):
    class Meta:
        model = models.WeakSupervisionTask
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


class RecordTokenizationTask(SQLAlchemyObjectType):
    class Meta:
        model = models.RecordTokenizationTask
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


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


class LastRunAttributesResult(graphene.ObjectType):
    created_at = graphene.DateTime()
    state = graphene.String()
    iteration = graphene.Int()
    logs = graphene.List(graphene.DateTime)


class UserAttributeSampleRecordsResult(graphene.ObjectType):
    record_ids = graphene.List(graphene.ID)
    calculated_attributes = graphene.List(graphene.String)


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


class AdminMessage(SQLAlchemyObjectType):
    class Meta:
        model = models.AdminMessage
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)


class Task(graphene.ObjectType):
    id = graphene.ID()
    project_id = graphene.ID()
    created_by = graphene.ID()
    organization_name = graphene.String()
    project_name = graphene.String()
    state = graphene.String()
    task_type = graphene.String()
    started_at = graphene.DateTime()
    finished_at = graphene.DateTime()


class EmbeddingPlatform(graphene.ObjectType):
    platform = graphene.String()
    terms = graphene.String()
    gdpr_compliant = graphene.Boolean()


class TaskQueue(SQLAlchemyObjectType):
    class Meta:
        model = models.TaskQueue
        interfaces = (Node,)

    id = graphene.ID(source="id", required=True)
