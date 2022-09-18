import os
import re
import time
import datetime
import requests
import jsonpickle
import subprocess

from frontend import models
from framarama.base.client import ApiClient
from config import models as config_models
from config.utils import finishing


class Singleton:
    singletons = {}
    stamps = {}

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
        _configs = list(models.Config.objects.all())
        self._config = _configs[0] if len(_configs) else None

    def get_config(self):
        return self._config


class ApiResult:

    def __init__(self, data, mapper):
        self._data = data
        self._mapper = mapper

    def _map(self, data):
        return self._mapper(data)


class ApiResultItem(ApiResult):

    def __init__(self, data, mapper):
        super().__init__(data, mapper)
        self._item = None

    def get(self, name, default=None):
        return self._data.get(name, default)

    def item(self):
        if self._item is None:
            self._item = self._map(self._data)
        return self._item


class ApiResultList(ApiResult):

    def __init__(self, data, mapper):
        super().__init__(data, mapper)
        self._items = None

    def count(self):
        return self._data.get('count', 0)

    def items(self):
        if self._items is None:
            self._items = [self._map(_item) for _item in self._data['results']]
        return self._items

    def get(self, index):
        return self.items()[index]


class ApiClient(Singleton):

    def __init__(self):
        super().__init__()
        _config = Config.get().get_config()
        if _config:
            if _config.mode == 'local':
                self._base_url = 'http://127.0.0.1:8000'
            else:
                self._base_url = _config.cloud_server
            self._display_access_key = _config.cloud_display_access_key
        if self._base_url == None or self._display_access_key == None:
            raise Exception("Missing base URL or display access key")
        self._base_url = self._base_url.rstrip('/') + '/api'
        self._display_access_key = self._display_access_key

    def _request(self, path):
        _headers = {}
        _headers['X-Display'] = self._display_access_key
        _response = requests.get(self._base_url + path, headers=_headers)
        _response.raise_for_status()
        return _response.json()

    def _list(self, mapper):
        _data = ApiResultList()
        return _data

    def get_display(self):
        _data = self._request('/displays')
        if 'results' in _data and len(_data['results']):
            return ApiResultItem(
                _data['results'][0],
                lambda d: config_models.Display(**{k: v for k, v in d.items() if k not in ['device_type_name', 'frame']}))
        return None

    def get_items_list(self, display_id):
        return ApiResultList(
            self._request('/displays/{}/items/all'.format(display_id)),
            lambda d: config_models.Item(**{k: v for k, v in d.items() if k not in ['rank']}))

    def get_items_next(self, display_id):
        _result = ApiResultList(
            self._request('/displays/{}/items/next'.format(display_id)),
            lambda d: config_models.Item(**{k: v for k, v in d.items() if k not in ['rank']}))
        return _result.get(0) if _result.count() > 0 else None

    def get_finishings(self, display_id):
        return ApiResultList(
            self._request('/displays/{}/finishings'.format(display_id)),
            lambda d: config_models.Finishing(**d))


class Filesystem:

    @staticmethod
    def file_write(filename, data):
        with open(filename, 'wb') as f:
            f.write(data)

    @staticmethod
    def file_rotate(path, pattern, fmt, count, extensions=[]):
        _files = []
        with os.scandir(path) as it:
            _files = [entry for entry in it if entry.is_file()]
            _files = [entry for entry in _files if re.match(pattern, entry.name)]
            _files = [entry.name for entry in _files]
            _files.sort(reverse=True)
            _files = _files[-count:]

        for _i, _name in enumerate(_files):
            (_num, _ext) = re.match(pattern, _name).groups()
            _new_num = len(_files)-_i+1

            for _ext in extensions:
                _old_name = path + fmt.format(int(_num), _ext)
                _new_name = path + fmt.format(_new_num, _ext)
                os.rename(_old_name, _new_name)
        
        return {_ext: path + fmt.format(1, _ext) for _ext in extensions}

    @staticmethod
    def exec_run(args):
        _result = subprocess.run(args, capture_output=True, shell=True)
        if _result.returncode == 0:
            return _result.stdout
        else:
            print("Error: {}{}".format(_result.stdout, _result.stderr))
        return None

    @staticmethod
    def exec_search(executable):
        return Filesystem.exec_run(["which", executable])

    @staticmethod
    def exec_running(executable):
        return Filesystem.exec_run(['pidof', executable])


class Frontend(Singleton):

    def __init__(self):
        super().__init__()

    def get_config(self):
        return Config.get(self)

    def get_display(self):
        return Display.get(self)

    def get_device(self):
        return FrontendDevice.get(self)


class Display(Singleton):

    def __init__(self):
        super().__init__()
        self._client = ApiClient.get()
        self._data = self._client.get_display()
        self._items = None
        self._next = None
        self._finishings = None

    def display(self):
        return self._data.item()

    def frame(self):
        return ApiResultItem(
            self._data.get('frame'),
            lambda d: config_models.Frame(**d)).item()

    def get_id(self):
        return self._data.item().id

    def get_name(self):
        return self._data.item().name

    def get_enabled(self):
        return self._data.item().enabled

    def get_device_type(self):
        return self._data.item().device_type

    def get_device_type_name(self):
        return self._data.get('device_type_name')

    def get_device_width(self):
        return self._data.item().device_width

    def get_device_height(self):
        return self._data.item().device_height

    def get_time_change(self):
        _time = datetime.time.fromisoformat(self._data.get('time_change', '00:05:00'))
        _time_change = datetime.timedelta(hours=_time.hour, minutes=_time.minute)
        return _time_change

    def time_change_reached(self, last_update):
        _now = datetime.datetime.utcnow()
        _time_change = self.get_time_change()
        return last_update is None or _now - _time_change > last_update

    def get_items(self):
        if self._items == None:
            self._items = self._client.get_items_list(self.get_id())
        return self._items

    def get_next_item(self, refresh=True):
        if self._next is None or refresh:
            self._next = self._client.get_items_next(self.get_id())
        return self._next

    def get_finishings(self, refresh=True):
        if self._finishings is None or refresh:
            self._finishings = self._client.get_finishings(self.get_id())
        return self._finishings


class FrontendDevice(Singleton):

    def __init__(self):
        super().__init__()
        self._finisher = DefaultFrontendFinisher()
        self._renderers = [
            DefaultFrontendRenderer(),
            FilesystemFrontendRenderer(),
            VisualizeFrontendRenderer(),
        ]

    def finish(self, display, item, finishings):
        return self._finisher.process(display, item, finishings)

    def render(self, display, item):
        for renderer in self._renderers:
            renderer.process(display, item)


class FrontendItem:

    def __init__(self, item, result):
        self._item = item
        self._result = result

    def item(self):
        return self._item

    def data(self):
        return self._result.get_data()

    def mime(self):
        return self._result.get_mime()


class BaseFrontendFinisher:

    def process(self, display, item, finishings):
      pass


class DefaultFrontendFinisher(BaseFrontendFinisher):

    def process(self, display, item, finishings):
        _processor = finishing.Processor(finishing.Context(
            display.display(),
            display.frame(),
            item,
            finishings.items(),
            finishing.WandImageProcessingAdapter()))
        return FrontendItem(item, _processor.process())


class BaseFrontendRenderer:

    def process(self, display, item):
        pass


class DefaultFrontendRenderer(BaseFrontendRenderer):

    def process(self, display, item):
        pass


class FilesystemFrontendRenderer(BaseFrontendRenderer):
    FILE_PATH = '/tmp/'
    FILE_PATTERN = r'^framarama-(\d+)\.(json)$'
    FILE_FORMAT = 'framarama-{:05d}.{:s}'

    def process(self, display, item):
        _files = Filesystem.file_rotate(
            self.FILE_PATH,
            self.FILE_PATTERN,
            self.FILE_FORMAT,
            5,
            ['json', 'image'])

        with open(_files['json'], 'w') as f:
            f.write(jsonpickle.encode({
              'item': item.item(),
              'mime': item.mime()
            }))

        with open(_files['image'], 'wb') as f:
            f.write(item.data())


class VisualizeFrontendRenderer(BaseFrontendRenderer):
    CMD_FEH = ['feh', '--fullscreen', '--auto-zoom', '--stretch', '--auto-rotate', '--scale-down', '-bg-fill', '/tmp/picture-background.jpg', '-f', '/tmp/picture-current.csv', '--reload', '10']
    CMD_IMAGICK = ['magick', 'display', '-window', 'root']

    def __init__(self):
        self._update = None

    def discover(self):
        _cmds = ['feh', 'magick']
        for _cmd in _cmds:
            _path = Filesystem.exec_search(_cmd)
            if _path:
                self._update = getattr(self, 'update_' + _cmd)

    def update_feh(self, display, item):
        if Filesystem.exec_running('feh') is None:
            print("start feh")
        if not Filesystem.file_exists('/tmp/picture-current.csv'):
            Filesystem.file_write('/tmp/picture-current.csv', '/tmp/framarama-1.image')
    
    def update_magic(self, display, item):
        Filesystem.exec_run(self.CMD_IMAGICK + ['/tmp/framarama-1.image'])

    def process(self, display, item):
        if self._update == None:
            self.discover()
        if self._update == None:
            return
        self._update(display, item)

