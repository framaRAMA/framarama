import os
import re
import io
import time
import datetime
import requests
import jsonpickle
import subprocess
import threading
import logging

from django.conf import settings
from django.apps import apps
from django.core import management
from django.utils import timezone
from django.db import connections
from django.contrib.auth.models import User

from frontend import models
from framarama.base.client import ApiClient
from config import models as config_models
from config.utils import finishing


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
        _configs = list(models.Config.objects.all())
        self._config = _configs[0] if len(_configs) else None

    def get_config(self):
        return self._config

    def is_local_mode(self):
        return self._config.mode == 'local'


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
        return self._data.get(name, default) if self._data else None

    def item(self):
        if self._data is None:
            return None
        if self._item is None:
            self._item = self._map(self._data)
        return self._item


class ApiResultList(ApiResult):

    def __init__(self, data, mapper):
        super().__init__(data, mapper)
        self._items = None

    def count(self):
        return self._data.get('count', 0) if self._data else None

    def items(self):
        if self._data is None:
            return None
        if self._items is None:
            self._items = [self._map(_item) for _item in self._data['results']]
        return self._items

    def get(self, index):
        return self.items()[index]


class ApiClient(Singleton):

    def __init__(self):
        super().__init__()
        self._base_url = None
        self._display_access_key = None
        _config = Config.get().get_config()
        if _config:
            if _config.mode == 'local':
                self._base_url = 'http://127.0.0.1:8000'
            else:
                self._base_url = _config.cloud_server
            self._display_access_key = _config.cloud_display_access_key
            self._base_url = self._base_url.rstrip('/') + '/api'
            self._display_access_key = self._display_access_key

    def configured(self):
        return self._base_url != None and self._display_access_key != None

    def _request(self, path):
        if not self.configured():
            raise Exception("API client not configured")
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
        if _data and 'results' in _data and len(_data['results']):
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
    def file_match(path, pattern):
        _files = []
        with os.scandir(path) as it:
            _files = [entry for entry in it if entry.is_file()]
            _files = [entry for entry in _files if re.match(pattern, entry.name)]
            _files = [entry.name for entry in _files]
            _files.sort(reverse=True)
            _files = [(_file,) + re.match(pattern, _file).groups() for _file in _files]
        return _files

    @staticmethod
    def file_rotate(path, pattern, fmt, count, extensions=[]):
        _files = Filesystem.file_match(path, pattern)
        _files = _files[-count:]

        for _i, (_name, _num, _ext) in enumerate(_files):
            #(_num, _ext) = re.match(pattern, _name).groups()
            _new_num = len(_files)-_i+1

            for _ext in extensions:
                _old_name = path + fmt.format(int(_num), _ext)
                _new_name = path + fmt.format(_new_num, _ext)
                os.rename(_old_name, _new_name)
        
        return {_ext: path + fmt.format(1, _ext) for _ext in extensions}


class Process:

    @staticmethod
    def exec_run(args):
        _result = subprocess.run(args, capture_output=True, shell=True)
        if _result.returncode == 0:
            return _result.stdout
        else:
            logger.error("Error running {}: {}{}".format(args, _result.stdout, _result.stderr))
        return None

    @staticmethod
    def exec_search(executable):
        return Process.exec_run(["which", executable, '||', 'exit', '0'])

    @staticmethod
    def exec_running(executable):
        return Process.exec_run(['pidof', executable])


class Frontend(Singleton):
    INIT_PHASE_START = 0
    INIT_PHASE_DB_DEFAULT = 1   # Check if frontend/default DB is available
    INIT_PHASE_CONFIGURED = 2   # Frontend configuration exists
    INIT_PHASE_DB_CONFIG = 3    # Check if config DB is available
    INIT_PHASE_API_ACCESS = 4   # API access possible

    def __init__(self):
        super().__init__()
        self._client = None
        self._init_phase = Frontend.INIT_PHASE_START
        self._initialized = False   # database setup
        self._configured = False    # frontend config exists
        self._db_access = False     # DB access for config
        self._api_access = False    # API acccess configured

    def _mgmt_cmd(self, *args, **kwargs):
        _out, _err = io.StringIO(), io.StringIO()
        management.call_command(*args, **kwargs, stdout=_out, stderr=_err)
        return _out.getvalue().rstrip("\n").split("\n")

    def _init_connections(self):
        from framarama import settings
        settings_db = settings.configure_databases()

    def _init_migrations(self, database):
        _migrations = self._mgmt_cmd('showmigrations', '--plan', no_color=True, database=database)
        _migrations = [_line.rsplit(' ', 1) for _line in _migrations]
        _migrations = [_name for _status, _name in _migrations if _status.strip() != '[X]']
        if len(_migrations):
            logger.info("Applying {} missing migrations to {}".format(len(_migrations), database))
            management.call_command('migrate', database=database)
        logger.info("Migrations for {} complete!".format(database))

    def _init_admin_user(self):
        _users = User.objects.filter(is_superuser=True).all()
        if len(_users) == 0:
            logger.info("Creating admin user")
            User.objects.create_user(
                username=settings.FRAMARAMA['ADMIN_USERNAME'],
                email=settings.FRAMARAMA['ADMIN_MAIL'],
                password=settings.FRAMARAMA['ADMIN_PASSWORD'],
                is_superuser=True)
            _users = User.objects.filter(username=settings.FRAMARAMA['ADMIN_USERNAME']).all()
        logger.info("Admin user is {}".format(_users[0]))

    def initialize(self):
        if self._init_phase < Frontend.INIT_PHASE_DB_DEFAULT:
            self._init_connections()
            self._init_migrations('default')
            self._init_phase = Frontend.INIT_PHASE_DB_DEFAULT
            self._initialized = True
        if self._init_phase < Frontend.INIT_PHASE_CONFIGURED:
            #_table_names = connections['default'].introspection.table_names()
            #_config_table = apps.get_model('frontend', 'config')._meta.db_table
            #if _config_table in _table_names:
            _configs = list(models.Config.objects.all())
            if len(_configs) == 0:
                logger.info("Creating default configuration")
                _config = models.Config()
                _config.save()
                _configs.append(_config)
            self._configured = _configs[0].mode != None
            if self._configured:
                self._init_phase = Frontend.INIT_PHASE_CONFIGURED
        if self._init_phase < Frontend.INIT_PHASE_DB_CONFIG:
            self._init_admin_user()
            self._init_migrations('config')
            self._init_phase = Frontend.INIT_PHASE_DB_CONFIG
            self._db_access = True
        if self._configured and not self._api_access:
            _client = ApiClient.get()
            if _client.configured():
                self._api_access = True
                self._client = _client
                self._init_phase = Frontend.INIT_PHASE_API_ACCESS
        return self._initialized and self._configured

    def is_initialized(self):
        return self._initialized

    def is_configured(self):
        return self._initialized and self._configured

    def db_access(self):
        return self._db_access

    def api_access(self):
        return self.is_configured() and self._api_access

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
        _now = timezone.now()
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
        self._renderer_filesystem = FilesystemFrontendRenderer()
        self._renderers = [
            DefaultFrontendRenderer(),
            self._renderer_filesystem,
            VisualizeFrontendRenderer(),
            WebsiteFrontendRenderer(),
        ]

    def finish(self, display, item, finishings):
        return self._finisher.process(display, item, finishings)

    def render(self, display, item):
        for renderer in self._renderers:
            renderer.process(display, item)

    def get_files(self):
        return self._renderer_filesystem.files()


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

    def width(self):
        return self._result.get_width()

    def height(self):
        return self._result.get_height()


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
    FILE_PATH = settings.FRAMARAMA['DATA_PATH']
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
              'mime': item.mime(),
              'time': datetime.datetime.utcnow()
            }))

        with open(_files['image'], 'wb') as f:
            f.write(item.data())

    def files(self):
        _files = {}
        for (_file, _num, _ext) in Filesystem.file_match(self.FILE_PATH, self.FILE_PATTERN):
            _file_image = self.FILE_FORMAT.format(int(_num), 'image')
            _json = open(self.FILE_PATH + '/' + _file, 'r').read()
            _image = open(self.FILE_PATH + '/' + _file_image, 'rb').read()
            _files[_file] = {
                'json': jsonpickle.decode(_json),
                'image': _image
            }
        return _files


class VisualizeFrontendRenderer(BaseFrontendRenderer):
    DATA_PATH = settings.FRAMARAMA['DATA_PATH']
    CMD_FEH = ['feh', '--fullscreen', '--auto-zoom', '--stretch', '--auto-rotate', '--scale-down', '-bg-fill', DATA_PATH + '/picture-background.jpg', '-f', DATA_PATH + '/picture-current.csv', '--reload', '10']
    CMD_IMAGICK = ['magick', 'display', '-window', 'root']

    def __init__(self):
        self._update = None

    def discover(self):
        _cmds = ['feh', 'magick']
        for _cmd in _cmds:
            _path = Process.exec_search(_cmd)
            if _path:
                self._update = getattr(self, 'update_' + _cmd)

    def update_feh(self, display, item):
        if Process.exec_running('feh') is None:
            print("start feh")
        if not Filesystem.file_exists(DATA_PATH + '/picture-current.csv'):
            Filesystem.file_write(DATA_PATH + '/picture-current.csv', DATA_PATH + '/framarama-1.image')
    
    def update_magic(self, display, item):
        Process.exec_run(self.CMD_IMAGICK + [DATA_PATH + '/framarama-1.image'])

    def process(self, display, item):
        if self._update == None:
            self.discover()
        if self._update == None:
            return
        self._update(display, item)


