from enum import Enum
import re


class UpdateStatus(Enum):
    NEEDED = 1
    NOT_NEEDED = 2
    FIRST_DOWNLOAD = 3


class Pattern(Enum):
    WEBM = re.compile(r'\/\/([\w\.\/]+\.webm)')
    GIF = re.compile(r'\/\/([\w\.\/]+\.gif)')
    FILENAME = re.compile(r'\/(\d+\.\w{1,4})')


class Extension(Enum):
    WEBM = 'webm'
    GIF = 'gif'
    JPG = 'jpg'


class Infos(object):
    def __init__(self, url, thread_id, extensions, files):
        self.url = url
        self.thread_id = thread_id
        self.extensions = extensions
        self.files = files
