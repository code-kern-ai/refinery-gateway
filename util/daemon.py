import threading


def run(target, *args, **kwargs):
    threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True,).start()
