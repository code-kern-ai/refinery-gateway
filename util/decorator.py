from threading import Timer
from inspect import signature

from datetime import datetime, timedelta
from functools import wraps


def debounce(wait):
    def decorator(fn):
        sig = signature(fn)
        caller = {}

        def debounced(*args, **kwargs):
            nonlocal caller

            try:
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                called_args = fn.__name__ + str(dict(bound_args.arguments))
            except:
                called_args = ""

            def call_it(key):
                try:
                    caller.pop(key)
                except:
                    pass

                fn(*args, **kwargs)

            try:
                # Always try to cancel timer
                caller[called_args].cancel()
            except:
                pass

            caller[called_args] = Timer(wait, call_it, [called_args])
            caller[called_args].start()

        return debounced

    return decorator


class throttle(object):
    """
    Decorator that prevents a function from being called more than once every
    time period.
    To create a function that cannot be called more than once a minute:
        @throttle(minutes=1)
        def my_fun():
            pass
    """

    def __init__(self, seconds=0, minutes=0, hours=0):
        self.throttle_period = timedelta(seconds=seconds, minutes=minutes, hours=hours)
        self.time_of_last_call = datetime.min

    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            now = datetime.now()
            time_since_last_call = now - self.time_of_last_call

            if time_since_last_call > self.throttle_period:
                self.time_of_last_call = now
                return fn(*args, **kwargs)

        return wrapper


class param_throttle(object):
    """
    Decorator that prevents a function from being called more than once every
    time period. Expects a function parameter as first argument via *args. This will be checked and compared.
    Example:
    @param_throttle(seconds=30)
    def send_project_update(project_id, message, is_global=False):
        --> same project_id call only once every x - new project_id has its own time comparison

    """

    def __init__(self, seconds=0, minutes=0, hours=0):
        self.throttle_period = timedelta(seconds=seconds, minutes=minutes, hours=hours)
        self.time_of_last_call = {None: datetime.min}

    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            now = datetime.now()
            first_param = args[0]
            if first_param in self.time_of_last_call:
                time_since_last_call = now - self.time_of_last_call[first_param]
                call = True if time_since_last_call > self.throttle_period else False
            else:
                call = True
            if call:
                self.time_of_last_call[first_param] = now
                return fn(*args, **kwargs)

        return wrapper
