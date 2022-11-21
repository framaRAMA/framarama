import os
import re
import time
import subprocess
import threading
import logging

from frontend import models


logger = logging.getLogger(__name__)


class Singleton:
    singletons = {}
    stamps = {}
    lock = threading.Lock()
    locks = {}

    def __init__(self):
        self._ts = Singleton._stamp()

    @staticmethod
    def _stamp():
        return round(time.time() * 1000)

    @classmethod
    def clear(cls, dependend=None):
        if dependend:
            Singleton.singletons.pop(dependend.__name__)
            Singleton.stamps.pop(dependend.__name__)
        else:
            Singleton.singletons = {}

    @classmethod
    def get(cls, dependend=None, force=False):
        _cls_name = cls.__name__
        with Singleton.lock:
            if _cls_name not in Singleton.locks:
                Singleton.locks[_cls_name] = threading.Lock()
        with Singleton.locks[_cls_name]:
            if force or (dependend and dependend._ts > Singleton.stamps.get(_cls_name, 0)):
                Singleton.singletons.pop(_cls_name, None)
                Singleton.stamps.pop(_cls_name, None)
            if _cls_name not in Singleton.singletons:
                Singleton.singletons[_cls_name] = cls()
                Singleton.stamps[_cls_name] = Singleton._stamp()
        return Singleton.singletons[_cls_name]


class Config(Singleton):

    def __init__(self):
        super().__init__()
        self._config = None

    def get_config(self):
        if self._config is None:
            _configs = list(models.Config.objects.all())
            self._config = _configs[0] if len(_configs) else None
        return self._config

    def is_local_mode(self):
        return self._config.mode == 'local'


class Filesystem:

    @staticmethod
    def file_read(filename):
        with open(filename, 'rb') as f:
            buf = f.read()
        return buf

    @staticmethod
    def file_write(filename, data):
        with open(filename, 'wb') as f:
            f.write(data)

    @staticmethod
    def file_match(path, pattern):
        _files = []
        with os.scandir(path) as it:
            _files = [entry for entry in it if entry.is_file()]
            _files = [entry for entry in _files if re.match(pattern, entry.name)]
            _files = [entry.name for entry in _files]
            _files.sort(reverse=False)
            _files = [(_file,) + re.match(pattern, _file).groups() for _file in _files]
        return _files

    @staticmethod
    def file_exists(filename):
        return os.path.exists(filename)

    @staticmethod
    def file_size(filename):
        return os.path.getsize(filename)

    @staticmethod
    def file_rotate(path, pattern, fmt, count, extensions=[]):
        _files = Filesystem.file_match(path, pattern)
        _files.reverse()
        _leftovers = _files[0:-count]
        _files = _files[-count:]

        for _i, (_name, _num, _ext) in enumerate(_files):
            _new_num = len(_files)-_i+1

            for _ext in extensions:
                _old_name = path + fmt.format(int(_num), _ext)
                _new_name = path + fmt.format(_new_num, _ext)
                os.rename(_old_name, _new_name)
        
        for _i, (_name, _num, _ext) in enumerate(_leftovers):
            for _ext in extensions:
                _current_name = path + fmt.format(int(_num), _ext)
                os.unlink(_current_name)

        return {_ext: path + fmt.format(1, _ext) for _ext in extensions}


class Process:

    @staticmethod
    def exec_run(args):
        _result = subprocess.run(args, capture_output=True)
        if _result.returncode == 0:
            return _result.stdout
        else:
            logger.error("Error running {}: code={}, stdout={}, stderr={}".format(' '.join(args), _result.returncode, _result.stdout, _result.stderr))
        return None

    @staticmethod
    def exec_bg(args):
        return subprocess.Popen(args)

    @staticmethod
    def exec_search(executable):
        return Process.exec_run(["which", executable])

    @staticmethod
    def exec_running(executable):
        return Process.exec_run(['pidof', executable])


