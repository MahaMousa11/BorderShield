# Minimal patched YOLOv5 utils for offline Jetson runtime

import contextlib
import threading

def emojis(s=""):
    return s

def threaded(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread
    return wrapper

class TryExcept(contextlib.ContextDecorator):
    def __init__(self, msg=""):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        if value:
            print(f"{self.msg}: {value}" if self.msg else value)
        return True
