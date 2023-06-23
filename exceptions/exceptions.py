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

class BadPasswordError(Exception):
    pass
