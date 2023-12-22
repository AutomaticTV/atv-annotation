import os
import glob
import mimetypes

import datetime
from bson import ObjectId
import bson.json_util as json_util

from .config import Config
from .connection import CLIENT, DB, DESCENDING, ASCENDING

json_loads = json_util.loads
json_util.loads = lambda x: json_loads(x.decode("utf-8") if isinstance(x, bytes) else x)

import threading
from functools import wraps
def delay(delay=0.):
    """
    Decorator delaying the execution of a function for a while.
    """
    def wrap(f):
        @wraps(f)
        def delayed(*args, **kwargs):
            timer = threading.Timer(delay, f, args=args, kwargs=kwargs)
            timer.start()
        return delayed
    return wrap
class Timer():
    toClearTimer = False
    def setTimeout(self, fn, time):
        isInvokationCancelled = False
        @delay(time)
        def some_fn():
                if (self.toClearTimer is False):
                        fn()
                else:
                    print('Invokation is cleared!')        
        some_fn()
        return isInvokationCancelled
    def setClearTimer(self):
        self.toClearTimer = True

def is_video(file_path):
    return os.path.isfile(file_path) and mimetypes.guess_type(file_path)[0].split('/')[0] == 'video'

def is_zip(file_path):
    mime_list = ["application/x-bzip", "application/x-bzip2", "application/x-rar-compressed", "application/x-tar", "application/zip", "application/x-7z-compressed"]
    mime = mimetypes.guess_type(file_path)[0]
    return mime in mime_list

def is_file(file_path):
    return os.path.isfile(file_path) and mimetypes.guess_type(file_path)[0].split('/')[0] == 'image'

def get_annotation(file_path):
    file_path = os.path.splitext(file_path)[0] + Config.ANNOTATION_FILE
    if os.path.isfile(file_path):
        return file_path
    return None

def is_annotation(file_path):
    return os.path.isfile(file_path) and os.path.splitext(file_path)[1].lower() == Config.ANNOTATION_FILE