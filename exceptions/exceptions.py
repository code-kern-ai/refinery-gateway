class NotificationTypeException(Exception):
    pass


class NotificationLevelException(Exception):
    pass


class TooManyRecordsForStaticSliceException(Exception):
    pass


class NoSuchDataSliceFoundException(Exception):
    pass


class MissingArgumentsException(Exception):
    pass


class NotAllowedInDemoError(Exception):
    pass


class NotAllowedInOpenSourceError(Exception):
    pass


class BadPasswordError(Exception):
    pass


class ApiTokenImportError(Exception):
    pass


class ProjectAccessError(Exception):
    pass


class ServiceRequestsError(Exception):
    pass


class DatabaseSessionError(Exception):
    pass


class ProjectManagerError(Exception):
    pass


class PayloadSchedulerError(Exception):
    pass


class EmbeddingConnectorError(Exception):
    pass


class AuthManagerError(Exception):
    pass
