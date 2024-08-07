from typing import Any, List, Dict, Optional, Union
from pydantic import (
    BaseModel,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    ConfigDict,
)


"""
Pydantic models for FastAPI.
"""


class StringBody(BaseModel):
    value: StrictStr


class ListStringBody(BaseModel):
    value: List[StrictStr]


class SearchRecordsBySimilarityBody(BaseModel):
    embeddingId: StrictStr
    recordId: StrictStr
    attFilter: Any = None
    recordSubKey: Any = None


class SearchRecordsExtendedBody(BaseModel):
    filterData: Any = None
    offset: StrictInt
    limit: StrictInt


class RecordsByStaticSliceBody(BaseModel):
    orderBy: Any = None
    offset: Any = None
    limit: Any = None


class ZeroShot10Body(BaseModel):
    heuristicId: StrictStr
    labelNames: List[StrictStr]


class ZeroShotTextBody(BaseModel):
    heuristicId: StrictStr
    config: StrictStr
    text: StrictStr
    runIndividually: StrictBool
    labelNames: List[StrictStr]


class CreateLabelsBody(BaseModel):
    labelingTaskId: StrictStr
    labels: List[StrictStr]


class CreateLabelBody(BaseModel):
    labelName: StrictStr
    labelingTaskId: StrictStr
    labelColor: StrictStr


class DeleteRecordLabelAssociationBody(BaseModel):
    recordId: StrictStr
    associationIds: Optional[List[StrictStr]] = []


class CreateDataSliceBody(BaseModel):
    name: StrictStr
    static: StrictBool
    filterRaw: StrictStr
    filterData: Any = None


class AvailableLinksBody(BaseModel):
    assumedRole: Optional[StrictStr] = None
    assumedHeuristicId: Optional[StrictStr] = None


class HuddleDataBody(BaseModel):
    huddleId: Optional[StrictStr] = None
    huddleType: Optional[StrictStr] = None


class WarningDataBody(BaseModel):
    warning_data: Dict


class LinkRouteBody(BaseModel):
    link_route: StrictStr


class GenerateAccessLinkBody(BaseModel):
    type: StrictStr
    id: StrictStr


class LockAccessLinkBody(BaseModel):
    link_id: StrictStr
    lock_state: StrictBool


class UpdateDataSliceBody(BaseModel):
    data_slice_id: StrictStr
    static: StrictBool
    filter_raw: StrictStr
    filter_data: List[StrictStr]


class UploadCredentialsAndIdBody(BaseModel):
    file_name: StrictStr
    file_type: StrictStr
    file_import_options: StrictStr
    upload_type: StrictStr
    key: Optional[StrictStr] = None


class RecordIdeBody(BaseModel):
    code: StrictStr


class NotificationsBody(BaseModel):
    project_filter: List[StrictStr]
    level_filter: List[StrictStr]
    type_filter: List[StrictStr]
    user_filter: StrictBool
    limit: StrictInt = 50


class RecordSyncBody(BaseModel):
    changes: Dict


class CreateHeuristicBody(BaseModel):
    labeling_task_id: StrictStr
    type: StrictStr
    description: StrictStr
    source_code: StrictStr
    name: StrictStr


class InitWeakSuperVisionBody(BaseModel):
    overwrite_default_precision: Optional[Union[StrictFloat, StrictInt]] = None
    overwrite_weak_supervision: Optional[Dict[str, Union[StrictFloat, StrictInt]]] = (
        None
    )


class CreateZeroShotBody(BaseModel):
    target_config: StrictStr
    labeling_task_id: StrictStr
    attribute_id: StrictStr


class UpdateHeuristicBody(BaseModel):
    labeling_task_id: StrictStr
    code: StrictStr
    description: StrictStr
    name: StrictStr


class RunThenWeakSupervisionBody(BaseModel):
    heuristic_id: StrictStr
    labeling_task_id: StrictStr


class CancelZeroShotBody(BaseModel):
    heuristic_id: StrictStr
    payload_id: StrictStr


class AddClassificationLabelBody(BaseModel):
    record_id: StrictStr
    labeling_task_id: StrictStr
    label_id: StrictStr
    as_gold_star: Optional[StrictBool] = None
    source_id: Optional[StrictStr] = None


class AddExtractionLabelBody(BaseModel):
    record_id: StrictStr
    labeling_task_id: StrictStr
    label_id: StrictStr
    as_gold_star: Optional[StrictBool] = None
    token_start_index: Optional[StrictInt] = None
    token_end_index: Optional[StrictInt] = None
    value: Optional[StrictStr] = None
    source_id: Optional[StrictStr] = None


class SetGoldStarBody(BaseModel):
    record_id: StrictStr
    labeling_task_id: StrictStr
    gold_user_id: StrictStr


class RemoveGoldStarBody(BaseModel):
    record_id: StrictStr
    labeling_task_id: StrictStr


class CreateOrganizationBody(BaseModel):
    name: StrictStr


class AddUserToOrganizationBody(BaseModel):
    user_mail: StrictStr
    organization_name: StrictStr


class RemoveUserToOrganizationBody(BaseModel):
    user_mail: StrictStr


class ChangeOrganizationBody(BaseModel):
    org_id: StrictStr
    changes: StrictStr


class DeleteOrganizationBody(BaseModel):
    name: StrictStr


class CreateAdminMessageBody(BaseModel):
    text: StrictStr
    level: StrictStr
    archive_date: StrictStr
    scheduled_date: Optional[StrictStr] = None


class ArchiveAdminMessageBody(BaseModel):
    message_id: StrictStr
    archived_reason: StrictStr


class UpdateConfigBody(BaseModel):
    dict_str: StrictStr


class ChangeUserRoleBody(BaseModel):
    user_id: StrictStr
    role: StrictStr


class CreatePersonalTokenBody(BaseModel):
    name: StrictStr
    scope: StrictStr
    expires_at: StrictStr


class CreateNewAttributeBody(BaseModel):
    name: StrictStr
    data_type: StrictStr


class UpdateKnowledgeBaseBody(BaseModel):
    knowledge_base_id: StrictStr
    name: Optional[StrictStr] = None
    description: Optional[StrictStr] = None


class AddTermToKnowledgeBaseBody(BaseModel):
    value: StrictStr
    comment: StrictStr
    knowledge_base_id: Union[StrictStr, List[StrictStr]]


class PasteKnowledgeTermsBody(BaseModel):
    knowledge_base_id: Union[StrictStr, List[StrictStr]]
    values: StrictStr
    split: StrictStr
    delete: StrictBool


class UpdateTermBody(BaseModel):
    term_id: StrictStr
    value: StrictStr
    comment: StrictStr


class UpdateAttributeBody(BaseModel):
    attribute_id: StrictStr
    name: Optional[StrictStr] = None
    data_type: Optional[StrictStr] = None
    is_primary_key: Optional[StrictBool] = None
    source_code: Optional[StrictStr] = None
    visibility: Optional[StrictStr] = None


class CalculateUserAttributeAllRecordsBody(BaseModel):
    attribute_id: StrictStr


class ModelProviderDeleteModelBody(BaseModel):
    # model_config is not an actual field, but configuration for Pydantic
    # https://docs.pydantic.dev/latest/api/config/
    model_config = ConfigDict(protected_namespaces=())
    model_name: StrictStr


class ModelProviderDownloadModelBody(BaseModel):
    # model_config is not an actual field, but configuration for Pydantic
    # https://docs.pydantic.dev/latest/api/config/
    model_config = ConfigDict(protected_namespaces=())
    model_name: StrictStr


class DeleteUserAttributeBody(BaseModel):
    attribute_id: StrictStr


class CreateTaskAndLabelsBody(BaseModel):
    labeling_task_name: StrictStr
    labeling_task_type: StrictStr
    labeling_task_target_id: Optional[StrictStr] = None
    labels: List[StrictStr]


class UpdateProjectNameAndDescriptionBody(BaseModel):
    name: StrictStr
    description: StrictStr


class CreateProjectBody(BaseModel):
    name: StrictStr
    description: StrictStr


class CreateSampleProjectBody(BaseModel):
    name: StrictStr
    project_type: StrictStr


class UpdateProjectTokenizerBody(BaseModel):
    tokenizer: StrictStr


class UpdateProjectStatusBody(BaseModel):
    new_status: StrictStr


class PrepareProjectExportBody(BaseModel):
    export_options: Any = None
    key: Optional[StrictStr] = None


class PrepareRecordExportBody(BaseModel):
    export_options: Any = None
    key: Optional[StrictStr] = None


class CreateEmbeddingBody(BaseModel):
    attribute_id: StrictStr
    config: StrictStr


class UpdateEmbeddingBody(BaseModel):
    embedding_id: StrictStr
    filter_attributes: List[StrictStr]


class UpdateLabelingTaskBody(BaseModel):
    labeling_task_id: StrictStr
    labeling_task_name: StrictStr
    labeling_task_type: StrictStr
    labeling_task_target_id: Optional[StrictStr] = None


class CreateLabelingTaskBody(BaseModel):
    labeling_task_name: StrictStr
    labeling_task_type: StrictStr
    labeling_task_target_id: Optional[StrictStr] = None


class UpdateLabelColorBody(BaseModel):
    labeling_task_label_id: StrictStr
    label_color: StrictStr


class UpdateLabelHotkeyBody(BaseModel):
    labeling_task_label_id: StrictStr
    label_hotkey: StrictStr


class UpdateLabelNameBody(BaseModel):
    label_id: StrictStr
    new_name: StrictStr


class CreateCommentBody(BaseModel):
    comment: StrictStr
    xftype: StrictStr
    xfkey: StrictStr
    project_id: Optional[StrictStr] = None
    is_private: Optional[StrictBool] = None


class DeleteCommentBody(BaseModel):
    comment_id: StrictStr
    project_id: Optional[StrictStr] = None


class UpdateCommentBody(BaseModel):
    comment_id: StrictStr
    changes: Dict
    project_id: Optional[StrictStr] = None


class TokenizedRecordBody(BaseModel):
    record_id: StrictStr


class UserLanguageDisplay(BaseModel):
    user_id: str
    language_display: str


class MappedSortedPaginatedUsers(BaseModel):
    sort_key: str
    sort_direction: int
    offset: int
    limit: int
    filter_minutes: int


class DeleteUserBody(BaseModel):
    user_id: StrictStr


class CancelTaskBody(BaseModel):
    project_id: StrictStr
    task_id: StrictStr
    task_type: StrictStr


class AttributeCalculationTaskExecutionBody(BaseModel):
    organization_id: StrictStr
    project_id: StrictStr
    user_id: StrictStr
    attribute_id: StrictStr


class InformationSourceTaskExecutionBody(BaseModel):
    project_id: StrictStr
    information_source_id: StrictStr
    information_source_type: StrictStr
    user_id: StrictStr


class DataSliceActionExecutionBody(BaseModel):
    project_id: StrictStr
    user_id: StrictStr
    embedding_id: StrictStr


class WeakSupervisionActionExecutionBody(BaseModel):
    project_id: StrictStr
    user_id: StrictStr
