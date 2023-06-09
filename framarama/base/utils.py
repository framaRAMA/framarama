import os
import re
import time
import datetime
import zoneinfo
import shutil
import subprocess
import threading
import signal
import logging
import json
import importlib

from django.utils import dateparse, timezone

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
    def file_copy(source, target):
        shutil.copyfile(source, target)

    @staticmethod
    def file_delete(filename):
        os.remove(filename)

    @staticmethod
    def file_match(path, pattern, files=True, dirs=False, recurse=None, prefix=None):
        _dirs = []
        _files = []
        _prefix = '' if prefix is None else prefix + '/'
        with os.scandir(path + '/' + _prefix) as it:
            for entry in it:
                if entry.is_dir() and (dirs or recurse):
                    _dirs.append(entry.name)
                if entry.is_file() and files == True and re.match(pattern, entry.name):
                    _files.append(entry.name)
        _files.sort(reverse=False)
        _files = [(_prefix + _file,) + re.match(pattern, _file).groups() for _file in _files]
        if dirs:
            _files.extend([(_prefix + _dir,) for _dir in _dirs])
        if recurse:
            for _dir in _dirs:
                _files.extend(Filesystem.file_match(
                    path,
                    pattern=pattern,
                    files=files,
                    dirs=dirs,
                    recurse=recurse-1 if type(recurse) == int else recurse,
                    prefix=_prefix + _dir))
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
    def exec_run(args, silent=False, env=None, sudo=False):
        if sudo:
            if 'sudo' not in args[0]:
                raise Exception("Error checking sudo permssion: Command does not contain sudo command: {}".format(args))
            _sudo_check = args.copy()
            _sudo_check.insert(1, '-l')
            if Process.exec_run(_sudo_check, silent=True) is None:
                return None
        _result = subprocess.run(args, env=env, capture_output=True)
        if _result.returncode == 0:
            _args = ' '.join([str(_arg) for _arg in args])
            logger.info('Run "{}": code={}, stdout={} bytes, stderr={} bytes'.format(_args, _result.returncode, len(_result.stdout), len(_result.stderr)))
            return _result.stdout
        elif not silent:
            _args = ' '.join([str(_arg) for _arg in args])
            logger.error('Error running "{}": code={}, stdout={}, stderr={}'.format(_args, _result.returncode, _result.stdout, _result.stderr))
        return None

    @staticmethod
    def exec_bg(args, **kwargs):
        return subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, **kwargs)

    @staticmethod
    def exec_search(executable):
        return Process.exec_run(["which", executable], True)

    @staticmethod
    def exec_running(executable):
        _pid = Process.exec_run(['pidof', executable])
        return int(_pid) if _pid else None

    @staticmethod
    def terminate(pid, timeout=5):
        os.kill(pid, signal.SIGTERM)
        while timeout > 0:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                return True
            timeout = timeout - 1
        return False

    @staticmethod
    def eval(code, global_vars={}, local_vars={}):
        return eval(code, global_vars, local_vars)


class Json:

    @staticmethod
    def from_dict(data):
        return json.dumps(data)

    @staticmethod
    def to_dict(data):
        return json.loads(data)

    @staticmethod
    def to_object_dict(data, fields, delim='_', prefix=''):
        _result = {}
        for _name, _value in data.items():
            if type(_value) == dict:
                _not_mapped = {}
                for _result_name, _result_value in Json.to_object_dict(_value, fields, delim, prefix + _name + delim).items():
                    if _result_name in fields:
                        _result[_result_name] = _result_value
                    else:
                        _not_mapped[_result_name[len(prefix)+1:]] = _result_value
                if len(_not_mapped):
                    _result[prefix + _name] = json.dumps(_not_mapped)
            elif type(_value) == list:
                _result[prefix + _name] = json.dumps(_value)
            else:
                _result[prefix + _name] = _value
        return _result

    @staticmethod
    def from_object_dict(data, delim='_', prefix=''):
        _result = {}
        for _name in [_name for _name in data if _name.startswith(prefix)]:
            _value = data[_name]
            _suffix = _name[len(prefix):]
            if delim in _suffix:
                _key = _suffix.split(delim)[0]
                _result[_key] = Json.from_object_dict(data, delim, prefix + _key + delim)
            elif type(_value) == str and len(_value) > 0 and _value[0] in ['[', '{', '"']:
                _result[_suffix] = json.loads(_value)
            else:
                _result[_suffix] = _value
        return _result


class DateTime:

    @staticmethod
    def tz(tz=None):
        if tz is None:
            return timezone.get_current_timezone()
        if type(tz) == zoneinfo.ZoneInfo:
            return tz
        return zoneinfo.ZoneInfo(tz)

    @staticmethod
    def as_tz(time, tz):
        return time.replace(tzinfo=DateTime.tz(tz))

    @staticmethod
    def get(time, sub=None, add=None, tz=None):
        if sub:
            time = time - DateTime.delta(sub)
        if add:
            time = time + DateTime.delta(add)
        return time.astimezone(DateTime.tz(tz))

    @staticmethod
    def now(sub=None, add=None, tz=None):
        return DateTime.get(timezone.now(), sub=sub, add=add, tz=tz)

    @staticmethod
    def midnight(time=None, tz=None):
        _time = time if time else DateTime.now(tz=tz)
        return _time.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def delta(time=None, days=None, hours=None, minutes=None, seconds=None):
        if type(time) == datetime.timedelta:
            return time
        if type(time) == int or type(time) == float:
            return datetime.timedelta(seconds=time)
        if time != None:
            _time = datetime.time.fromisoformat(time)
            return datetime.timedelta(hours=_time.hour, minutes=_time.minute, seconds=_time.second)
        if days != None or hours != None or minutes != None or seconds != None:
            return datetime.timedelta(
                days=days if days else 0,
                hours=hours if hours else 0,
                minutes=minutes if minutes else 0,
                seconds=seconds if seconds else 0)
        return None

    @staticmethod
    def delta_dict(delta):
        _seconds = DateTime.delta(delta).total_seconds()
        return {
            'total': _seconds,
            'seconds': int(_seconds % 60),
            'minutes': int(_seconds % 3600 / 60),
            'hours': int(_seconds % 86400 / 3600),
            'days': int(_seconds / 86400),
        }

    @staticmethod
    def reached(time, delta):
        return time is None or time + delta < DateTime.now()

    @staticmethod
    def in_range(time, deltas):
        if type(deltas) == dict:
            _deltas = deltas
        else:
            _deltas = {i: v for i, v in enumerate(deltas)}
        _keys = list(_deltas)
        _reached = None
        for _key in _keys[1:]:
            if DateTime.reached(time, _deltas[_key]):
                _reached = _key
        if _reached is None and len(_deltas):
            if DateTime.reached(time, _deltas[_keys[0]]):
                _reached = _keys[0]
            else:
                _reached = _keys[-1]
        if type(deltas) == dict:
            return _reached
        return _deltas[_reached] if _reached is not None else None

    @staticmethod
    def utc(dt):
        if dt and dt.tzinfo:
            return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
        elif dt:
            return dt.isoformat() + 'Z'
        return None

    @staticmethod
    def parse(date):
        return dateparse.parse_datetime(date)

    @staticmethod
    def zoned(tz):
        class Zoned:
            def __init__(self, tz):
                self._tz = tz
                self._changed = False
            def __enter__(self):
                self._changed = self._tz and self._tz != timezone.get_current_timezone_name()
                if self._changed:
                    timezone.activate(tz)
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self._changed:
                    timezone.deactivate()
        return Zoned(tz)


class Classes:

    @staticmethod
    def load(name, fqcn=False, fallback=None):
        if fqcn:
            _name, _, _class = name.rpartition('.')
        else:
            _name = name
        try:
            _module = importlib.import_module(_name)
            if fqcn:
                if hasattr(_module, _class):
                    return getattr(_module, _class)
                raise ModuleNotFoundError("Class {} does not exists in {}".format(_class, _module))
            else:
                return _module
        except Exception as e:
            if fallback:
                return Classes.load(fallback, fqcn)
            raise e

    @staticmethod
    def subclasses(clazz, root=True):
        _classes = [clazz] if root else []
        for _clazz in clazz.__subclasses__():
            _classes.extend(Classes.subclasses(_clazz))
        return _classes
