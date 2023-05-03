from exceptions import exceptions
from submodules.model import enums

__notification_data = {
    enums.NotificationType.IMPORT_STARTED.value: {
        "message_template": "Started import.",
        "title": "Data import",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.IMPORT_DONE.value: {
        "message_template": "Completed import.",
        "title": "Data import",
        "level": enums.Notification.SUCCESS.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.IMPORT_FAILED.value: {
        "message_template": "Import of @@arg@@ failed.",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.CONVERTING_DATA.value: {
        "message_template": "Converting data for the upload.",
        "title": "Data import",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.INVALID_FILE_TYPE.value: {
        "message_template": "File type @@arg@@ is currently not supported.",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.FILE_TYPE_NOT_GIVEN.value: {
        "message_template": "No filetype was given.",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.UNKNOWN_PARAMETER.value: {
        "message_template": "Unknown parameter for import options: @@arg@@.",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.UPLOAD_CONVERSION_FAILED.value: {
        "message_template": "Upload conversion failed: @@arg@@.",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.NEW_ROWS_EXCEED_MAXIMUM_LIMIT.value: {
        "message_template": "Rows exceed maximum allowed amount (@@arg@@/@@arg@@).",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.TOTAL_ROWS_EXCEED_MAXIMUM_LIMIT.value: {
        "message_template": "Rows would exceed maximum amount after upload (@@arg@@/@@arg@@).",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.COLS_EXCEED_MAXIMUM_LIMIT.value: {
        "message_template": "Columns exceed maximum allowed amount (@@arg@@/@@arg@@).",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.COL_EXCEED_MAXIMUM_LIMIT.value: {
        "message_template": "Attribute @@arg@@ exceeds maximum allowed character count (@@arg@@/@@arg@@).",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.DUPLICATED_COLUMNS.value: {
        "message_template": "The attributes @@arg@@ are not unique. Please contact the support.",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.DUPLICATED_TASK_NAMES.value: {
        "message_template": "The task names @@arg@@ are not unique. Please contact the support.",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.DIFFERENTIAL_ATTRIBUTES.value: {
        "message_template": "Attributes @@arg@@ are missing in your file. Please contact the support.",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.NON_EXISTENT_TARGET_ATTRIBUTE.value: {
        "message_template": "Attributes @@arg@@ are not present as targets in your file. Please contact the support.",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.DUPLICATED_COMPOSITE_KEY.value: {
        "message_template": "Please upload a file with your projects primary key(s).",
        "title": "Data import",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.INFORMATION_SOURCE_STARTED.value: {
        "message_template": "Started heuristic @@arg@@.",
        "title": "Heuristic execution",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.INFORMATION_SOURCES.value,
        "docs": enums.DOCS.INFORMATION_SOURCES.value,
    },
    enums.NotificationType.INFORMATION_SOURCE_COMPLETED.value: {
        "message_template": "Completed heuristic @@arg@@.",
        "title": "Heuristic execution",
        "level": enums.Notification.SUCCESS.value,
        "page": enums.Pages.INFORMATION_SOURCES.value,
        "docs": enums.DOCS.INFORMATION_SOURCES.value,
    },
    enums.NotificationType.INFORMATION_SOURCE_FAILED.value: {
        "message_template": "Heuristic @@arg@@ failed. You can contact the support if you need help.",
        "title": "Heuristic execution",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.INFORMATION_SOURCES.value,
        "docs": enums.DOCS.INFORMATION_SOURCES.value,
    },
    enums.NotificationType.INFORMATION_SOURCE_CANT_FIND_EMBEDDING.value: {
        # extracted embedding name, task name, task type (attribute or token)
        "message_template": 'Can\'t find matching embedding for "@@arg@@" on task @@arg@@.',
        "title": "Embedding information",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.INFORMATION_SOURCES.value,
        "docs": enums.DOCS.INFORMATION_SOURCES.value,
    },
    enums.NotificationType.INFORMATION_SOURCE_S3_EMBEDDING_MISSING.value: {
        # embedding s3 file name, embedding name
        "message_template": "Embedding object missing from S3 storage. Try recreating embedding @@arg@@.",
        "title": "Embedding information",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.INFORMATION_SOURCES.value,
    },
    enums.NotificationType.INFORMATION_SOURCE_S3_DOCBIN_MISSING.value: {
        "message_template": "Tokenization docs missing in S3 storage. Docs are present once tokenization process is started (not queued).",
        "title": "Heuristic execution",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.INFORMATION_SOURCES.value,
    },
    enums.NotificationType.WEAK_SUPERVISION_TASK_STARTED.value: {
        "message_template": "Started weak supervision.",
        "title": "Weak supervision",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.INFORMATION_SOURCES.value,
        "docs": enums.DOCS.WEAK_SUPERVISION.value,
    },
    enums.NotificationType.WEAK_SUPERVISION_TASK_DONE.value: {
        "message_template": "Completed weak supervision.",
        "title": "Weak supervision",
        "level": enums.Notification.SUCCESS.value,
        "page": enums.Pages.INFORMATION_SOURCES.value,
        "docs": enums.DOCS.WEAK_SUPERVISION.value,
    },
    enums.NotificationType.WEAK_SUPERVISION_TASK_FAILED.value: {
        "message_template": "Could not start weak supervision.",
        "title": "Weak supervision",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.INFORMATION_SOURCES.value,
        "docs": enums.DOCS.WEAK_SUPERVISION.value,
    },
    enums.NotificationType.WEAK_SUPERVISION_TASK_NO_VALID_LABELS.value: {
        "message_template": "Can't start weak supervision without valid est. precision.",
        "title": "Weak supervision",
        "level": enums.Notification.WARNING.value,
        "page": enums.Pages.INFORMATION_SOURCES.value,
        "docs": enums.DOCS.WEAK_SUPERVISION.value,
    },
    enums.NotificationType.IMPORT_SAMPLE_PROJECT.value: {
        "message_template": "Copying sample project into workspace.",
        "title": "Sample project",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.OVERVIEW.value,
        "docs": enums.DOCS.CREATING_PROJECTS.value,
    },
    enums.NotificationType.COLLECTING_SESSION_DATA.value: {
        "message_template": "Collecting data for the labeling session.",
        "title": "Session information",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.LABELING.value,
        "docs": enums.DOCS.WORKFLOW.value,
    },
    enums.NotificationType.SESSION_INFO.value: {
        "message_template": "This session holds the first @@arg@@ records. Adjust your filter to collect a different set.",
        "title": "Session information",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.LABELING.value,
        "docs": enums.DOCS.WORKFLOW.value,
    },
    enums.NotificationType.SESSION_RECORD_AMOUNT_CHANGED.value: {
        "message_template": "The amount of records that have been collected changed.",
        "title": "Session information",
        "level": enums.Notification.WARNING.value,
        "page": enums.Pages.LABELING.value,
        "docs": enums.DOCS.WORKFLOW.value,
    },
    enums.NotificationType.WRONG_USER_FOR_SESSION.value: {
        "message_template": "Requested session belongs to a different user.",
        "title": "Session information",
        "level": enums.Notification.WARNING.value,
        "page": enums.Pages.LABELING.value,
        "docs": enums.DOCS.WORKFLOW.value,
    },
    enums.NotificationType.KNOWLEDGE_BASE_ALREADY_EXISTS.value: {
        "message_template": "List @@arg@@ already exists.",
        "title": "Lookup lists",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.KNOWLEDGE_BASE.value,
        "docs": enums.DOCS.KNOWLEDGE_BASE.value,
    },
    enums.NotificationType.TERM_ALREADY_EXISTS.value: {
        "message_template": "Term @@arg@@ already exists for list @@arg@@.",
        "title": "Lookup lists",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.KNOWLEDGE_BASE.value,
        "docs": enums.DOCS.KNOWLEDGE_BASE.value,
    },
    enums.NotificationType.INVALID_PRIMARY_KEY.value: {
        "message_template": "The selected primary key combination is not valid.",
        "title": "Data schema",
        "level": enums.Notification.WARNING.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.UPLOADING_DATA.value,
    },
    enums.NotificationType.PROJECT_DELETED.value: {
        "message_template": "Deleted project @@arg@@.",
        "title": "Project information",
        "level": enums.Notification.SUCCESS.value,
        "page": enums.Pages.OVERVIEW.value,
        "docs": enums.DOCS.CREATING_PROJECTS.value,
    },
    enums.NotificationType.MISSING_REFERENCE_DATA.value: {
        "message_template": "@@arg@@",
        "title": "Data management",
        "level": enums.Notification.WARNING.value,
        "page": enums.Pages.INFORMATION_SOURCES.value,
        "docs": enums.DOCS.INFORMATION_SOURCES.value,
    },
    enums.NotificationType.DATA_SLICE_ALREADY_EXISTS.value: {
        "message_template": "Filter with name @@arg@@ already exists.",
        "title": "Data management",
        "level": enums.Notification.WARNING.value,
        "page": enums.Pages.DATA.value,
        "docs": enums.DOCS.DATA_BROWSER.value,
    },
    enums.NotificationType.DATA_SLICE_CREATION_FAILED.value: {
        "message_template": "Filter creation failed. Please contact the support with the error log @@arg@@.",
        "title": "Data management",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.DATA.value,
        "docs": enums.DOCS.DATA_BROWSER.value,
    },
    enums.NotificationType.DATA_SLICE_UPDATE_FAILED.value: {
        "message_template": "Filter update failed. Please contact the support with the error log @@arg@@.",
        "title": "Data management",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.DATA.value,
        "docs": enums.DOCS.DATA_BROWSER.value,
    },
    enums.NotificationType.CUSTOM.value: {
        "message_template": "@@arg@@",
        "title": "Workflow information",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.OVERVIEW.value,
        "docs": enums.DOCS.WORKFLOW.value,
    },
    enums.NotificationType.TOKEN_CREATION_STARTED.value: {
        "message_template": "",
        "title": "Tokenization creation",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.CREATING_PROJECTS.value,
    },
    enums.NotificationType.TOKEN_CREATION_DONE.value: {
        "message_template": "",
        "title": "Tokenization creation",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.CREATING_PROJECTS.value,
    },
    enums.NotificationType.TOKEN_CREATION_FAILED.value: {
        "message_template": "",
        "title": "Tokenization creation",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.CREATING_PROJECTS.value,
    },
    enums.NotificationType.EMBEDDING_CREATION_STARTED.value: {
        "message_template": "",
        "title": "Embedding creation",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.CREATE_EMBEDDINGS.value,
    },
    enums.NotificationType.EMBEDDING_CREATION_DONE.value: {
        "message_template": "",
        "title": "Embedding creation",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.CREATE_EMBEDDINGS.value,
    },
    enums.NotificationType.EMBEDDING_CREATION_FAILED.value: {
        "message_template": "",
        "title": "Embedding creation",
        "level": enums.Notification.ERROR.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.CREATE_EMBEDDINGS.value,
    },
    enums.NotificationType.EMBEDDING_CREATION_WARNING.value: {
        "message_template": "",
        "title": "Embedding creation",
        "level": enums.Notification.WARNING.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.CREATE_EMBEDDINGS.value,
    },
    enums.NotificationType.IMPORT_ISSUES_WARNING.value: {
        "message_template": "Some labels couldn't be imported. Check task import_issues for more information.",
        "title": "Import issues",
        "level": enums.Notification.WARNING.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.CREATING_PROJECTS.value,
    },
    enums.NotificationType.UNKNOWN_DATATYPE.value: {
        "message_template": "Some attribute datatypes (@@arg@@) were converted to string since they are not natively supported by refinery.",
        "title": "Unknown categories",
        "level": enums.Notification.INFO.value,
        "page": enums.Pages.SETTINGS.value,
        "docs": enums.DOCS.CREATING_PROJECTS.value,
    },
}


def check_type_valid(notification_type: enums.NotificationType) -> None:
    if notification_type not in __notification_data:
        raise exceptions.NotificationTypeException(
            f"Type {notification_type} is not valid for notifications."
        )
