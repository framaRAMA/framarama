import os
import re
import sys
import time
import pathlib
import datetime
import zoneinfo
import collections
import shutil
import mimetypes
import subprocess
import threading
import signal
import logging
import json
import importlib
import traceback
import requests
import dateutil.parser

from django.utils import dateparse, timezone

from jinja2.sandbox import SandboxedEnvironment


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
            from frontend import models
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
    def file_append(filename, data):
        with open(filename, 'ab') as f:
            f.write(data)

    @staticmethod
    def file_copy(source, target):
        shutil.copyfile(source, target)

    @staticmethod
    def file_link(source, target):
        os.symlink(source, target)

    @staticmethod
    def file_delete(filename):
        os.remove(filename)

    @staticmethod
    def file_match(path, pattern, files=True, dirs=False, links=False, recurse=None, recurse_min=None, prefix=None):
        if not Filesystem.file_exists(path):
            return []
        _dirs = []
        _files = []
        _prefix = '' if prefix is None else prefix + '/'
        with os.scandir(path + '/' + _prefix) as it:
            for entry in it:
                if entry.is_dir() and (dirs or recurse):
                    _dirs.append(entry.name)
                if ((entry.is_file() and files == True) or (entry.is_symlink() and links == True)) and re.match(pattern, entry.name):
                    _files.append(entry.name)
        _files.sort(reverse=False)
        _files = [(_prefix + _file,) + re.match(pattern, _file).groups() for _file in _files]
        if dirs:
            if recurse is None or recurse_min is None or recurse_min <= 0:
                _files.extend([(_prefix + _dir,) for _dir in _dirs])
        if recurse:
            for _dir in _dirs:
                _files.extend(Filesystem.file_match(
                    path,
                    pattern=pattern,
                    files=files,
                    dirs=dirs,
                    recurse=recurse-1 if type(recurse) == int else -1,
                    recurse_min=recurse_min-1 if type(recurse_min) == int else None,
                    prefix=_prefix + _dir))
        return _files

    @staticmethod
    def file_exists(filename):
        return os.path.exists(filename)

    @staticmethod
    def file_size(filename):
        return os.path.getsize(filename)

    @staticmethod
    def file_mime(filename):
        _mime = mimetypes.guess_type(filename)
        return _mime[0] if _mime else None

    @staticmethod
    def file_rotate(path, pattern, fmt, count, extensions=[], start=0, reverse=False):
        _files = Filesystem.file_match(path, pattern)
        _leftovers = _files[count:]
        _files = _files[start:count]
        if not reverse:
            _files.reverse()
        elif len(_files):
            _files.pop(0)

        for _i, (_name, _num, _ext) in enumerate(_files):
            if not reverse:
                _new_num = start+len(_files)-_i+1
            else:
                _new_num = start+_i+1

            for _ext in extensions:
                _old_name = path + fmt.format(int(_num), _ext)
                _new_name = path + fmt.format(_new_num, _ext)
                os.rename(_old_name, _new_name)

        for _i, (_name, _num, _ext) in enumerate(_leftovers):
            for _ext in extensions:
                _current_name = path + fmt.format(int(_num), _ext)
                os.unlink(_current_name)

        return {_ext: path + fmt.format(start+1, _ext) for _ext in extensions}

    def path_normalize(path, root=None, absolute=False):
        if path is None:
            return None
        _root = pathlib.Path(root).resolve() if root else pathlib.Path.cwd()
        _path = pathlib.Path(path)
        _normalized = pathlib.Path(os.path.normpath(_root / _path))
        if root and not _normalized.is_relative_to(_root):
            return None
        _result = _normalized.absolute()
        if not absolute:
            _result = _result.relative_to(_root)
        return str(_result)

    def path_create(path):
        os.makedirs(path, exist_ok=True)

    def path_exists(path):
        return os.path.isdir(path)


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
        _global_vars = global_vars.copy()
        _global_vars['__builtins__'] = None
        _global_vars['__import__'] = None
        return eval(code, _global_vars, local_vars)


class Json:

    @staticmethod
    def from_dict(data, pretty=False):
        return json.dumps(data) if pretty == False else json.dumps(data, indent=4)

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
        if type(time) == datetime.time:
            return datetime.timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)
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
    def after(time1, time2):
        if time1 is None:
            return None
        if time2 is None:
            return None
        return time1 > time2

    @staticmethod
    def before(time1, time2):
        if time1 is None:
            return None
        if time2 is None:
            return None
        return time1 < time2

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
    def utc(dt, timestamp=False):
        if dt is None:
            return None
        if dt.tzinfo:
          _dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        else:
          _dt = dt
        return _dt.timestamp() if timestamp else _dt.isoformat() + 'Z'

    @staticmethod
    def parse(date):
        _result = dateparse.parse_datetime(date)
        if _result:
            return _result
        try:
            return dateutil.parser.parse(date)
        except:
            return None

    @staticmethod
    def format(date, fmt=None):
        _fmt = fmt if fmt else '%Y-%m-%d %H:%M:%S'
        return date.strftime(_fmt)

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


class Exceptions:

    @staticmethod
    def traceback():
        ex_type, ex_value, ex_trace = sys.exc_info()
        _traceback = traceback.format_exception(ex_type, ex_value, ex_trace)
        return _traceback[-1] + ''.join(_traceback[:-1])


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


class Lists:
    TREE_SEP = '.'

    @staticmethod
    def chunked(source, size):
        _result = []
        for _sid, _sval in source:
            _result.append((_sid, _sval))
            if len(_result) == size:
                yield _result
                _result[:] = []
        else:
            if len(_result):
                yield _result

    @staticmethod
    def process(source, target_match, target=None, source_match=None, size=100, create_func=None, update_func=None, delete_func=None):
        _stats = {'total': 0, 'create': 0, 'update': 0, 'delete': 0}
        for _svalues in Lists.chunked(source, size) if source else []:
            _smap = {_id: _val for _id, _val in _svalues}
            _sids = _smap.keys()
            _tvalues = target_match(_sids)
            _tmap = {_id: _val for _id, _val in _tvalues}
            _tids = _tmap.keys()
            for _id in [_id for _id in _sids if _id not in _tids]:  # set.difference(_sids, _tids):
                _stats['total'] = _stats['total'] + 1
                _stats['create'] = _stats['create'] + 1
                if create_func:
                    create_func(_id, _smap[_id])
            for _id in [_id for _id in _tids if _id not in _sids]:  # set.difference(_tids, _sids):
                _stats['total'] = _stats['total'] + 1
                _stats['delete'] = _stats['delete'] + 1
                if delete_func:
                    delete_func(_id, _tmap[_id])
            for _id in [_id for _id in _sids if _id in _tids]:  # set.intersection(_sids, _tids):
                _stats['total'] = _stats['total'] + 1
                _stats['update'] = _stats['update'] + 1
                if update_func:
                    update_func(_id, _smap[_id], _tmap[_id])
        for _tvalues in Lists.chunked(target, size) if target else []:
            _tmap = {_id: _val for _id, _val in _tvalues}
            _tids = _tmap.keys()
            _svalues = source_match(_tids) if source_match else []
            _smap = {_id: _val for _id, _val in _svalues}
            _sids = _smap.keys()
            for _id in [_id for _id in _tids if _id not in _sids]:  # set.difference(_tids, _sids):
                _stats['total'] = _stats['total'] + 1
                _stats['delete'] = _stats['delete'] + 1
                if delete_func:
                    delete_func(_id, _tmap[_id])
        return _stats

    @staticmethod
    def from_tree(items, child_name, parent_name, id_name=None, parent_id=None):
        _result = {}
        for _i, _item in enumerate(items):
            _id = _item[id_name] if id_name else "{}{}".format(parent_id+Lists.TREE_SEP if parent_id != None else "", _i)
            if type(_item) == dict:
                _item[parent_name] = parent_id
            elif type(_item) == object:
                setattr(_item, parent_name, parent_id)
            _result[_id] = _item
            if type(_item) == dict and child_name in _item:
                _result.update(Lists.from_tree(_item[child_name], child_name, parent_name, id_name, _id))
            elif type(_item) == object and hasattr(_item, child_name):
                _result.update(Lists.from_tree(getattr(_item, child_name), child_name, parent_name, id_name, _id))
        return _result

    @staticmethod
    def to_tree(items, parent_name='parent', child_name='children', path=''):
        _current = [{child_name: []}]
        _path = path
        _parent = None
        for _i, _item in items.items():
            _key = _i[len(_path):]
            if Lists.TREE_SEP in _key:  # child items
                _path = _i[0:len(_path)+_key.find(Lists.TREE_SEP)+1]
                _key = _i[len(_path):]
                _current.append(_current[-1][child_name][-1])
            if _key == '':  # back to parent
                _path = _i[0:_path.rfind(Lists.TREE_SEP)-1]
                _key = _i[len(_path):]
                _current.pop()
            _item[child_name] = []
            _item[parent_name] = _current[-1] if len(_current) > 1 else None
            _current[-1][child_name].append(_item)
        return _current[0][child_name]

    @staticmethod
    def from_annotated(items):
        _key = ""
        _key_next = ""
        _key_no = [0]
        _result = collections.OrderedDict()
        for _i, _annotate in enumerate(items):
            if _annotate[1]['open']:
                _key = _key + _key_next + "."
                _key_no.append(_i)
            _key_next = str(_i - _key_no[-1])
            _result[_key[1:] + _key_next] = _annotate[0]
            if _annotate[1]['close']:
                _key_count = 0
                for _close in _annotate[1]['close']:
                    _key = _key[0:_key.rindex(".")-1]
                    _key_count = _key_count + _i - _key_no.pop()
                _key_no[-1] = _key_no[-1] + _key_count + 1
        return _result

    @staticmethod
    def map_tree(items, func, child_name=None):
        _result = []
        for _item in items:
            _result.append(func(_item))
            if type(_item) == dict and child_name in _item:
                _result[-1][child_name] = Lists.map_tree(_item[child_name], func, child_name)
            elif type(_item) == object and hasattr(_item, child_name):
                setattr(_result[-1], child_name, Lists.map_tree(getattr(_item, child_name), func, child_name))
        return _result


class Network:
    METHOD_GET = 'GET'
    METHOD_POST = 'POST'
    METHOD_PUT = 'PUT'
    METHOD_HEAD = 'HEAD'

    @staticmethod
    def get_url(url, method, data=None, headers=None, user_agent={}, **kwargs):
        _headers = {}
        _headers['Connection'] = 'close'
        _headers['User-Agent'] = '/'.join(['framaRAMA'] + [_t+':'+str(_v) for _t, _v in user_agent.items() if _v])
        _headers.update(headers or {})
        if method == Network.METHOD_GET:
            _response = requests.get(url, timeout=(15, 30), headers=_headers, **kwargs)
        elif method == Network.METHOD_POST:
            if 'Content-Type' not in _headers:
                _headers['Content-Type'] = 'application/json; charset=utf-8'
                kwargs['json'] = data
            else:
                kwargs['data'] = data
            _response = requests.post(url, timeout=(15, 30), headers=_headers, **kwargs)
        else:
            raise Exception("Can not handle HTTP method {}".format(method))
        return _response


class Template:

    @staticmethod
    def _env():
        _env = SandboxedEnvironment()
        _env.keep_trailing_newline = True
        _env.filters['split'] = lambda v, sep=None, maxsplit=-1: str(v).split(sep, maxsplit)
        _env.filters['keys'] = lambda v: dict(v).keys()
        return _env

    @staticmethod
    def render(template, globals_vars={}):
        if template is None:
            return None
        _env = Template._env()
        _env.globals.update(globals_vars)
        return _env.from_string(template).render()

    @staticmethod
    def parse(template):
        if template is None:
            return None
        _env = Template._env()
        _env.parse(_env.from_string(template))
