import os
import io
import re
import sys
import time
import fcntl
import threading
import datetime
import jsonpickle
import base64
import logging
import django

from django.conf import settings
from django.core import management
from django.contrib.auth import get_user_model
from django.db import connections

from frontend import models
from framarama.base import device
from framarama.base.utils import Singleton, Config, Filesystem, Process, DateTime, Json
from framarama.base.api import ApiClient, ApiResultItem
from config.utils import context, finishing
from config import models as config_models


logger = logging.getLogger(__name__)


class Frontend(Singleton):
    INIT_PHASE_START = 0
    INIT_PHASE_STATIC = 1
    INIT_PHASE_DB_DEFAULT = 2
    INIT_PHASE_CONFIGURED = 3
    INIT_PHASE_DB_CONFIG = 4
    INIT_PHASE_SETUP = 5
    INIT_PHASE_API_ACCESS = 6
    INIT_PHASE_ERROR = 100
    INIT_PHASES = {
        INIT_PHASE_START: "Started",
        INIT_PHASE_STATIC: "Collect statics",
        INIT_PHASE_DB_DEFAULT: "Checking frontend database",
        INIT_PHASE_CONFIGURED: "Checking frontend configuration",
        INIT_PHASE_DB_CONFIG: "Checking config in database",
        INIT_PHASE_SETUP: "Checking setup configured",
        INIT_PHASE_API_ACCESS: "Checking API access",
        INIT_PHASE_ERROR: "Some error occurred, recovery mode"
    }
    INIT_FILE = settings.FRAMARAMA['DATA_PATH'] + '/framarama-init.json'
    BG_HINT_FILE = settings.FRAMARAMA['DATA_PATH'] + '/background.txt'

    def __init__(self):
        super().__init__()
        self._client = None
        self._init_phase = Frontend.INIT_PHASE_START

    def _bg_hint(self, msg):
        Filesystem.file_write(Frontend.BG_HINT_FILE, msg.encode())

    def _mgmt_cmd(self, *args, **kwargs):
        _out, _err = io.StringIO(), io.StringIO()
        management.call_command(*args, **kwargs, stdout=_out, stderr=_err)
        return _out.getvalue().rstrip("\n").split("\n")

    def _init_statics(self):
        _statics = self._mgmt_cmd('collectstatic', '--no-input')
        logger.info("Collect static executed: {}".format(_statics))

    def _init_database(self):
        from framarama import settings
        settings_db = settings.configure_databases()
        self._init_migrations('default')

    def _init_configuration(self):
        _configs = list(models.Config.objects.all())
        if len(_configs) == 0:
            logger.info("Creating default configuration")
            _config = models.Config()
            _config.save()
            _configs.append(_config)
            Singleton.clear()

    def _init_migrations(self, database):
        _migrations = self._mgmt_cmd('showmigrations', '--plan', no_color=True, database=database)
        _migrations = [_line.rsplit(' ', 1) for _line in _migrations]
        _migrations = [_name for _status, _name in _migrations if _status.strip() != '[X]']
        if len(_migrations):
            logger.info("Applying {} missing migrations to {}".format(len(_migrations), database))
            management.call_command('migrate', database=database)
        logger.info("Migrations for {} complete!".format(database))

    def _init_data(self):
        self._init_admin_user()
        if 'config' in connections:
            self._init_migrations('config')
        else:
            logger.info("Skipping migration of config because default is used")

    def _init_admin_user(self):
        _users = get_user_model().objects.filter(is_superuser=True).all()
        if len(_users) == 0:
            logger.info("Creating admin user")
            get_user_model().objects.create_user(
                username=settings.FRAMARAMA['ADMIN_USERNAME'],
                email=settings.FRAMARAMA['ADMIN_MAIL'],
                password=settings.FRAMARAMA['ADMIN_PASSWORD'],
                is_superuser=True)
            _users = get_user_model().objects.filter(username=settings.FRAMARAMA['ADMIN_USERNAME']).all()
        logger.info("Admin user is {}".format(_users[0]))

    def init_get(self):
        _init_file = Filesystem.file_exists(Frontend.INIT_FILE)
        return Json.to_dict(Filesystem.file_read(Frontend.INIT_FILE)) if _init_file else None

    def init_set(self, data):
        _init_file = Filesystem.file_exists(Frontend.INIT_FILE)
        if _init_file and data is None:
            Filesystem.file_delete(Frontend.INIT_FILE)
        elif data:
            Filesystem.file_write(Frontend.INIT_FILE, Json.from_dict(data).encode())

    def initialize(self):
        if self._init_phase >= Frontend.INIT_PHASE_ERROR:
            return False
        _pre_init_phases = {
            Frontend.INIT_PHASE_STATIC: self._init_statics,
            Frontend.INIT_PHASE_DB_DEFAULT: self._init_database,
            Frontend.INIT_PHASE_CONFIGURED: self._init_configuration,
            Frontend.INIT_PHASE_DB_CONFIG: self._init_data,
        }
        _last_pre_init_phase = list(_pre_init_phases.keys())[-1]
        if not self.init_get():
            logger.info("Starting system setup")
            for _phase, _method in _pre_init_phases.items():
                if self._init_phase < _phase:
                    self._bg_hint(Frontend.INIT_PHASES[_phase])
                    try:
                        _result = _method()
                        self._init_phase = _phase if _result is None else _result
                    except Exception as e:
                        logger.error("Error: initialization failed (phase {}): {}".format(_phase, e))
                        self._init_phase = Frontend.INIT_PHASE_ERROR + _phase
            if self._init_phase == _last_pre_init_phase:
                logger.info("System environment setup completed!")
                self.init_set(self.get_status())
                self._bg_hint("")
            else:
                _init_status = self.get_init_status()['phase']
                self._bg_hint("{}{}".format('Error: ' if _init_status['status'] == 'Error' else '', _init_status['name']))
        elif self._init_phase < _last_pre_init_phase:
            self._init_phase = _last_pre_init_phase
        if self.get_config().get_config() is None:
            return
        if self._init_phase < Frontend.INIT_PHASE_SETUP:
            _mode = self.get_config().get_config().mode
            if _mode != None and _mode.strip() != '':
                self._init_phase = Frontend.INIT_PHASE_SETUP
        if self.is_setup() and not self.api_access():
            _client = ApiClient.get()
            if _client.configured():
                self._client = _client
                self._init_phase = Frontend.INIT_PHASE_API_ACCESS
                _revision = self.get_device().get_capability().app_revision()
                _version = []
                if _revision and _revision['ref']:
                    _version.append(_revision['ref']['name'])
                if _revision and 'hash' in _revision:
                    _version.append(_revision['hash'])
                if len(_version):
                    self._client.register_user_agent('v', '-'.join(_version))
        return self.is_setup()

    def is_initialized(self):
        return self._init_phase >= Frontend.INIT_PHASE_DB_DEFAULT

    def is_configured(self):
        return self._init_phase >= Frontend.INIT_PHASE_CONFIGURED

    def is_setup(self):
        return self._init_phase >= Frontend.INIT_PHASE_SETUP

    def db_access(self):
        return self._init_phase >= Frontend.INIT_PHASE_DB_CONFIG

    def api_access(self):
        return self.is_configured() and self._init_phase >= Frontend.INIT_PHASE_API_ACCESS

    def get_init_status(self):
        _init_phase = self._init_phase
        if _init_phase >= Frontend.INIT_PHASE_ERROR:
            _init_phase = _init_phase - Frontend.INIT_PHASE_ERROR
            _status = 'Error '
        else:
            _status = 'Success'
        if _init_phase in Frontend.INIT_PHASES:
            _phase = Frontend.INIT_PHASES[_init_phase]
        else:
            _phase = 'Unknown'
        return {
            'phase': {
                'code': _init_phase,
                'status': _status,
                'name': _phase
            }
        }

    def get_config(self):
        return Config.get(self)

    def get_display(self, force=False):
        return Display.get(self, force=force)

    def get_device(self):
        return FrontendDevice.get(self)

    def get_screen(self):
        _capability = self.get_device().get_capability()
        _display_status = _capability.display_status()
        _display_size = _capability.display_size()
        return {
            'on': _display_status,
            'width': _display_size[0] if _display_size else None,
            'height': _display_size[1] if _display_size else None,
        }

    def get_status(self, restrictions=None):
        _config = self.get_config().get_config()
        _device = self.get_device()
        _capability = _device.get_capability()
        _data = {}
        if restrictions is None or 'sys' in restrictions:
            _container = os.environ.get('SERVER_SOFTWARE', '')
            if 'gunicorn' in _container:
                import gunicorn
                _container = 'gunicorn'
                _container_version = gunicorn.__version__
            elif 'uwsgi' in _container:
                import uwsgi
                _container = 'uwsgi'
                _container_version = uwsgi.version()
            elif 'mod_wsgi' in _container:
                import mod_wsgi
                _container = 'apache'
                _container_version = mod_wsgi.__version__
            else:
                _container = 'unknown'
                _container_version = 'unknown'
            _data['uptime'] = _capability.sys_uptime()
            _data['python'] = { 'version': sys.version.split()[0] }
            _data['django'] = { 'version': django.get_version() }
            _data['container'] = { 'name': _container, 'version' : _container_version }
            _os_info = _capability.os_info()
            _data['os'] = {
                'dist': _os_info.get('distibution') if _os_info else None,
                'name': _os_info.get('name') if _os_info else None,
                'version': _os_info.get('release') if _os_info else None
            }
        if restrictions is None  or 'memory' in restrictions:
            _mem_total = _capability.mem_total()
            _mem_free = _capability.mem_free()
            _data['memory'] = {
                'used': _mem_total - _mem_free if _mem_total and _mem_free else None,
                'free': _mem_free if _mem_free else None,
            }
        if restrictions is None  or 'cpu' in restrictions:
            _data['cpu'] = {
                'load': _capability.cpu_load(),
                'temp': _capability.cpu_temp(),
            }
        if restrictions is None  or 'disk' in restrictions:
            _disk_data = _capability.disk_data_free()
            _disk_tmp = _capability.disk_tmp_free()
            _data['disk'] = {
                'data': {
                    'used': _disk_data[0],
                    'free': _disk_data[1],
                },
                'tmp': {
                    'used': _disk_tmp[0],
                    'free': _disk_tmp[1],
                },
            }
        if restrictions is None  or 'network' in restrictions:
            _network_status = _device.network_status()
            _network_config = _capability.net_config()
            _data['network'] = {
                'profile': _network_status['profile'],
                'connected': DateTime.utc(_network_status['connected']) if _network_status['connected'] else None,
                'address': {
                    'ip': _network_config['ip'] if _network_config else None,
                    'gateway': _network_config['gateway'] if _network_config else None,
                }
            }
        if restrictions is None  or 'screen' in restrictions:
            _data['screen'] = self.get_screen()
        if restrictions is None  or 'item' in restrictions:
            _latest_items = [{
                'id': _file.item().id,
                'time': DateTime.utc(_file.time())
            } for _file in _device.get_items()]
            _data['items'] = {
                'total': _config.count_items,
                'shown': _config.count_views,
                'error': _config.count_errors,
                'updated': DateTime.utc(_config.date_items_update) if _config.date_items_update else None,
                'latest': _latest_items,
            }
        if restrictions is None  or 'app' in restrictions:
            _app_revision = _capability.app_revision()
            _data['app'] = {
                'uptime': (DateTime.now() - _config.date_app_startup).seconds if _config.date_app_startup else None,
                'date': DateTime.utc(_app_revision['date']) if _app_revision else None,
                'hash': _app_revision['hash'] if _app_revision else None,
                'branch': _app_revision['ref']['name'] if _app_revision else None,
                'revisions': _app_revision['revisions'] if _app_revision else None,
                'checked': DateTime.utc(_config.app_update_check_date) if _config.app_update_check_date else None,
                'installed': DateTime.utc(_config.app_update_install_date) if _config.app_update_install_date else None,
            }
        return _data

    def submit_status(self):
        _config = self.get_config().get_config()
        _restrictions = _config.cloud_status_restriction
        _display = self.get_display()
        _data = self.get_status(_restrictions if _restrictions else [])
        if not _data:
            return
        logger.info("Submitting {} status information: {}".format(_restrictions, _data))
        try:
            self._client.submit_status(_display.get_id(), _data)
        except Exception as e:
            logger.warning("Could not submit status information: {}".format(e))


class Display(Singleton):

    def __init__(self):
        super().__init__()
        self._client = ApiClient.get()
        self._data = self._client.get_display()
        self._client.register_user_agent('d', self.get_id())
        self._items = None
        self._next = None
        self._finishings = None
        self._contexts = None
        self._setting_vars = None
        self._setting_internals = None

    def display(self):
        return self._data.item()

    def frame(self):
        return self._data.item().frame

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

    def get_time_on(self):
        return self._data.item().time_on

    def time_on_reached(self):
        _time_on = self.get_time_on()
        return DateTime.now(sub=_time_on) > DateTime.midnight() if _time_on else False

    def get_time_off(self):
        return self._data.item().time_off

    def time_off_reached(self):
        _time_off = self.get_time_off()
        return DateTime.now(sub=_time_off) > DateTime.midnight() if _time_off else False

    def get_time_change(self):
        _time_change = self._data.get('time_change')
        return DateTime.delta(_time_change if _time_change else settings.FRAMARAMA['FRONTEND_ITEM_UPDATE_INTERVAL'])

    def time_change_reached(self, last_update):
        return last_update is None or last_update + self.get_time_change() < DateTime.now()

    def get_items(self, refresh=False):
        if self._items is None or refresh:
            self._items = self._client.get_items_list(self.get_id())
        return self._items

    def submit_item_hit(self, frontend_item, thumbnail=False):
        _item = frontend_item.item()
        _mime = frontend_item.mime()
        _meta = frontend_item.meta()
        _thumbnail = frontend_item.preview()
        _thumbnail_meta = {
            'width': frontend_item.preview_width(),
            'height': frontend_item.preview_height(),
        }
        _data = {
          'id': _item.id,
        }
        if _meta:
            _data.update({
                'duration_download': _meta['steps'][0]['duration'] if len(_meta['steps']) else None,
                'duration_finishing': _meta['duration'],
            })
        logger.info("Submit display item status: {}".format(_data))
        if thumbnail:
            self._client.submit_item_hit(self.get_id(), _data, _thumbnail, _mime, _thumbnail_meta)
        else:
            self._client.submit_item_hit(self.get_id(), _data)

    def submit_item_hit_error(self, item, ex):
        _data = {
          'id': item.id,
          'error_message': "{}: {}".format(type(ex).__name__, str(ex))
        }
        logger.info("Submit display item error status: {}".format(_data))
        self._client.submit_item_hit(self.get_id(), _data)

    def get_next_item(self, refresh=False):
        if self._next is None or refresh:
            self._next = self._client.get_items_next(self.get_id()).item()
        return self._next

    def get_contexts(self, refresh=False):
        if self._contexts is None or refresh:
            self._contexts = [_item.item() for _item in self._client.get_contexts(self.get_id()).items()]
        return self._contexts

    def get_finishings(self, refresh=False):
        if self._finishings is None or refresh:
            self._finishings = [_item.item() for _item in self._client.get_finishings(self.get_id()).items()]
        return self._finishings

    def get_setting_internals(self, refresh=False):
        if self._setting_internals is None or refresh:
            self._setting_internals = {}
            for _item in self._client.get_setting_internals().items():
                self._setting_internals.update({_item.item().name: _item.item().properties})
        return self._setting_internals

    def get_setting_variables(self, refresh=False):
        if self._setting_vars is None or refresh:
            self._setting_vars = {}
            for _item in self._client.get_setting_variables().items():
                self._setting_vars.update({_item.item().name: _item.item().properties})
        return self._setting_vars


class FrontendDevice(Singleton):
    DATA_PATH = settings.FRAMARAMA['DATA_PATH']
    FILE_PATTERN = r'^framarama-(\d+)\.(json)$'
    FILE_FORMAT = 'framarama-{:0>5}.{:s}'
    FILE_STREAM_PATTERN = r'^framarama-(stream)\.(json)$'
    FILE_STREAM_FORMAT = 'framarama-{}.{}'
    FILE_UPLOAD = DATA_PATH + '/framarama-upload.image'
    FILE_UPLOAD_JSON = DATA_PATH + '/framarama-upload.json'

    def __init__(self):
        super().__init__()
        self._monitor = FrontendMonitoring()
        self._network = {'started': None, 'connected': None, 'profile': None, 'previous': None, 'networks': None}
        self._renderers = {
            DefaultFrontendRenderer(),
            VisualizeFrontendRenderer(),
            WebsiteFrontendRenderer(),
        }
        self._capability = None
        self._display_status_force = None

    def _items_rotate(self, count_items_keep=None, start=0, reverse=False):
        return Filesystem.file_rotate(
            self.DATA_PATH,
            self.FILE_PATTERN,
            self.FILE_FORMAT,
            count_items_keep if count_items_keep else 6,
            ['json', 'image', 'preview'],
            start=start, reverse=reverse)

    def bg_hint(self, msg):
        Frontend.get()._bg_hint(msg)

    def monitor(self):
        return self._monitor

    def _finish(self, display, item, output):
        logger.info('Finishing item {}'.format(item))
        _context = finishing.Context(
            display.display(),
            display.frame(),
            display.get_contexts(True),
            item,
            display.get_finishings(True),
            display.get_setting_variables(),
            finishing.ImageProcessingAdapter.get_default(),
            self)
        with _context:
            _start = DateTime.now()
            _config = Frontend.get().get_config().get_config()
            _processor = finishing.Processor(_context)
            _processor.set_watermark(_config.watermark_type, _config.watermark_shift, _config.watermark_scale)
            _result = _processor.process()
            if _result:
                _json = jsonpickle.encode({
                  'item': item,
                  'image_meta': _result.get_image_meta(),
                  'preview_meta': _result.get_preview_meta(),
                  'meta': _result.get_meta(),
                  'time': DateTime.utc(DateTime.now()),
                  'usage_time': (DateTime.now() - _start).seconds,
                })

                _files = output()
                Filesystem.file_write(_files['json'], _json.encode())
                Filesystem.file_write(_files['image'], _result.get_image_data())
                Filesystem.file_write(_files['preview'], _result.get_preview_data())

                logger.info("Item finished in {} seconds ({} bytes, {}x{} pixels, mime {})!".format(
                    (DateTime.now() - _start).seconds,
                    len(_result.get_image_data()),
                    _result.get_image_width(),
                    _result.get_image_height(),
                    _result.get_image_mime()))
                return _result

    def finish_item(self, display, item):
        _config = Frontend.get().get_config().get_config()
        _result = self._finish(display, item, lambda: self._items_rotate(_config.count_items_keep))
        if _result:
            return self.get_items(0, count=1)[0]

    def finish_file(self, display, filename):
        _item = config_models.Item(**{'id_ext': -1, 'url': filename, 'date_creation': DateTime.now()})
        _result = self._finish(display, _item, lambda: {
            'json': self.DATA_PATH + self.FILE_STREAM_FORMAT.format('stream', 'json'),
            'image': self.DATA_PATH + self.FILE_STREAM_FORMAT.format('stream', 'image'),
            'preview': self.DATA_PATH + self.FILE_STREAM_FORMAT.format('stream', 'preview')
        })
        if _result:
            return self.get_streamed()[0]

    def activate(self, idx):
        _items = self.get_items(idx, count=1)
        if len(_items):
            self.activate_item(_items[0])

    def activate_item(self, item):
        for _renderer in self._renderers:
            _renderer.activate(item)

    def _get_items(self, file_pattern, file_format, count_items_keep, start=None, count=None):
        _files = []
        _items = None
        while _items is None:
            _items = Filesystem.file_match(self.DATA_PATH, file_pattern)[len(_files):]
            for _i, (_file, _num, _ext) in enumerate(_items):
                if start != None and start > _i:
                    continue
                if count != None and count == len(_files):
                    _items = []
                    break
                _file_json = self.DATA_PATH + '/' + _file
                _file_image = self.DATA_PATH + '/' + file_format.format(_num, 'image')
                _file_preview = self.DATA_PATH + '/' + file_format.format(_num, 'preview')
                try:
                    _files.append(FrontendItem(_file_json, _file_image, _file_preview))
                except Exception as e:
                    logger.warn('Removing non-readable item {}: {}'.format(_file_json, e))
                    self._items_rotate(count_items_keep, start=_i, reverse=True)
                    _items = None
                    start = _i
                    break;
        return _files

    def get_items(self, start=None, count=None):
        _config = Frontend.get().get_config().get_config()
        return self._get_items(self.FILE_PATTERN, self.FILE_FORMAT, _config.count_items_keep, start, count)

    def get_streamed(self):
        _config = Frontend.get().get_config().get_config()
        return self._get_items(self.FILE_STREAM_PATTERN, self.FILE_STREAM_FORMAT, 1)

    def upload_streamed(self, data, ts, final):
        if data is None:
            raise Error('No data')
        _chunks = list(data.chunks())
        if ts is None or str(ts) == "0":
            _chunk_data = _chunks.pop(0)
            _status = {'ts': int(DateTime.now().timestamp()*1000)}
            logger.info("Started streamed upload ({} bytes)".format(len(_chunk_data)))
            Filesystem.file_write(self.FILE_UPLOAD_JSON, Json.from_dict(_status).encode())
            Filesystem.file_write(self.FILE_UPLOAD, _chunk_data)
        else:
            _status = Json.to_dict(Filesystem.file_read(self.FILE_UPLOAD_JSON).decode())
            if _status['ts'] is ts:
                raise Error('Wrong ts given: ' + ts)
        for _chunk_data in _chunks:
            logger.info("Continued streamed upload ({} bytes)".format(len(_chunk_data)))
            Filesystem.file_append(self.FILE_UPLOAD, _chunk_data)
        if Filesystem.file_size(self.FILE_UPLOAD) > 20 * 1024 * 1024:
            raise Error('File too large')
        return _status

    def upload_file(self):
        return self.FILE_UPLOAD

    def network_connect(self, name):
        self.bg_hint("Connecting to network {}".format(name))
        self.get_capability().net_profile_connect(name=name)
        self._network['started'] = None
        self._network['connected'] = None
        self._network['previous'] = self._network['profile']
        self._network['profile'] = name
        self._network['networks'] = None

    def network_status(self):
        return self._network

    def network_ap_toggle(self):
        self.get_capability().net_toggle_ap()

    def network_verify(self):
        if self._network['connected']:
            return True
        _profile_list = self.get_capability().net_profile_list()
        _ap_active = self.get_capability().net_ap_active(_profile_list)
        if self._network['started'] is None:
            self._network['started'] = DateTime.now()
            logger.info("Checking network connectivity ...")
            if _ap_active:
                logger.info("Access Point active - disabling first!")
                self.network_ap_toggle()
            elif not self._network['profile'] is None:
                self.bg_hint("Checking network connectivity")
        if _ap_active:
            return False
        _profile_list = [_name for _name in _profile_list if _profile_list[_name]['active']]
        if len(_profile_list) == 0:
            if DateTime.now() - self._network['started'] > datetime.timedelta(seconds=30):
                _previous = self._network['previous']
                if _previous is None:
                    logger.info("Not connected within 30 seconds and no previous network available - starting access point")
                    self._network['networks'] = self.get_capability().net_wifi_list()
                    self.network_ap_toggle()
                    self._network['connected'] = DateTime.now()
                    self.bg_hint("Connect to framaRAMA and open http://framarama/")
                else:
                    logger.info("Not connected within 30 seconds - try to connect previous network {}".format(_previous))
                    self._network['profile'] = None
                    self._network['previous'] = None
                    self.network_connect(_previous)
                    self.bg_hint("Connecting to {}".format(_previous))
            else:
                _ip = self.get_capability().net_config()
                if _ip['ip']:
                    self._network['connected'] = DateTime.now()
                    self._network['profile'] = '(automatic)'
                    logger.info("Network already available ({})".format(_ip['ip']))
                else:
                    logger.info("Not connected!")
        elif _ap_active:
            self._network['connected'] = DateTime.now()
            self._network['profile'] = _profile_list[0]
            logger.info("Access point active!")
        else:
            self._network['connected'] = DateTime.now()
            self._network['profile'] = _profile_list[0]
            _ip = self.get_capability().net_config()
            _msg = "Connected to {} (IP {})".format(self._network['profile'], ','.join(_ip['ip']))
            logger.info(_msg)
            self.bg_hint(_msg)
            return True
        return False

    def display_toggle(self, state=None, force=False):
        _status = self.get_capability().display_status()
        _state = not _status if state is None else state
        _state_text = 'on' if _state else 'off'
        if _status != _state:
            if force:
                logger.info("Force display status {}".format(_state_text))
                self._display_status_force = _state
            elif self._display_status_force == _state:
                logger.info("Remove force display status {}".format(_state_text))
                self._display_status_force = None
            elif self._display_status_force is not None:
                _state = self._display_status_force
            if _status != _state:
                if _state:
                    self.get_capability().display_on()
                else:
                    self.get_capability().display_off()
                return _state
        elif self._display_status_force == _state:
            logger.info("Remove force display status {}".format(_state_text))
            self._display_status_force = None
        return None

    def get_capability(self):
        if self._capability is None:
            self._capability = device.Capabilities.discover()
        return self._capability


class FrontendMonitoring(threading.Thread):

    def __init__(self):
        super().__init__()
        self._xinput = None
        self._running = False
        self._key_events = []
        if Process.exec_search('xinput') and Process.exec_search('xmodmap'):
            self._xinput = True
        else:
            logger.warning("Not monitoring for keyboard events (xinput/xmodmap is missing)")

    def _verify_running(self):
        if self._xinput == None:
            return
        _pid = Process.exec_running('xinput')
        if _pid != None and self._xinput is True:
            Process.terminate(_pid)
        elif _pid is None and self._xinput != True:
            self._xinput.wait()
        elif self._xinput != True:
            return
        self._keymap = [_line.split() for _line in Process.exec_run(['xmodmap', '-pke']).split(b'\n')]
        self._keymap = {_map[1].decode(): _map[3].decode() for _map in self._keymap if len(_map)>3}
        self._xinput = Process.exec_bg(['xinput', 'test-xi2', '--root'], text=True, bufsize=1)
        self._xinput_keys = []
        fcntl.fcntl(self._xinput.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)

    def register_key_event(self, keys, method):
        self._key_events.append([set(keys), method])

    def start(self):
        if self._xinput == None:
            return
        self._running = True
        self._verify_running()
        super().start()

    def stop(self):
        self._running = False
        if self._xinput:
            self._xinput.terminate()
            try:
                self._xinput.wait(timeout=2)
            except:
                self._xinput.kill()
        super().stop()

    def run(self):
        _type = 'UNKNOWN'
        while self._running:
            time.sleep(0.01)
            for _parts in [_line.split() for _line in self._xinput.stdout.readlines()]:
                if len(_parts) == 0:
                    continue
                if _parts[0] == 'EVENT':
                    if _parts[3] in ['(KeyPress)', '(KeyRelease)']:
                        _type = _parts[3][1:-1]
                    else:
                        _type = 'UNKNOWN'
                elif _type == 'UNKNOWN':
                    pass
                elif _parts[0] != 'detail:':
                    pass
                elif _parts[1] in self._keymap:
                    _key = self._keymap[_parts[1]]
                    logger.info("Key event {} {} = {}".format(_type, _parts[1], _key))
                    if _type == 'KeyPress':
                        self._xinput_keys.append(_key)
                    elif _type == 'KeyRelease' and _key in self._xinput_keys:
                        self._xinput_keys.remove(_key)
                    _current = set(self._xinput_keys)
                    for _keys, _method in [_event for _event in self._key_events if _event[0] == _current]:
                        _method()


class FrontendItem:

    def __init__(self, file_json, file_image, file_preview):
        self._json = jsonpickle.decode(Filesystem.file_read(file_json))
        self._image = None
        self._image_file = file_image
        self._preview = None
        self._preview_file = file_preview

    def item(self):
        return self._json['item']

    def data(self):
        if self._image is None:
            self._image = Filesystem.file_read(self._image_file)
        return self._image

    def preview(self):
        if self._preview is None:
            self._preview = Filesystem.file_read(self._preview_file)
        return self._preview

    def time(self):
        return DateTime.parse(self._json['time'])

    def usage_time(self):
        return self._json['usage_time']

    def file(self):
        return self._image_file

    def mime(self):
        return self._json['image_meta']['mime']

    def width(self):
        return self._json['image_meta']['width']

    def height(self):
        return self._json['image_meta']['width']

    def preview_file(self):
        return self._preview_file

    def preview_mime(self):
        return self._json['preview_meta']['mime']

    def preview_width(self):
        return self._json['preview_meta']['width']

    def preview_height(self):
        return self._json['preview_meta']['width']

    def meta(self):
        return self._json['meta']


class BaseFrontendRenderer:
    DATA_PATH = settings.FRAMARAMA['DATA_PATH']
    COMMON_PATH = settings.FRAMARAMA['COMMON_PATH']
    FILE_LIST = DATA_PATH + '/framarama-current.csv'

    def activate(self, item):
        pass


class DefaultFrontendRenderer(BaseFrontendRenderer):
    pass


class VisualizeFrontendRenderer(BaseFrontendRenderer):
    IMG_CURRENT = BaseFrontendRenderer.DATA_PATH + '/framarama-current.image'

    def __init__(self):
        self._update = None

    def discover(self):
        _cmds = ['feh', 'magick']
        for _cmd in _cmds:
            if Process.exec_search(_cmd):
                self._update = getattr(self, 'update_' + _cmd)
                break

    def startup(self):
        if self._update == None:
            self.discover()
        if self._update == None:
            return
        self._update()

    def update_feh(self):
        _file_list = self.FILE_LIST
        if Process.exec_running('feh') is None:
            Process.exec_bg([
                'feh',
                '--fullscreen',
                '--auto-zoom',
                '--stretch',
                '--auto-rotate',
                '--scale-down',
                '-bg-trans',
                '-f', _file_list,
                '--reload', '2'
            ])
        if not Filesystem.file_exists(_file_list) or Filesystem.file_size(_file_list) == 0:
            Filesystem.file_write(_file_list, self.IMG_CURRENT.encode())
    
    def update_magic(self):
        Process.exec_run(self.CMD_IMAGICK + [self.IMG_CURRENT])

    def activate(self, item):
        Filesystem.file_copy(item.file(), self.IMG_CURRENT)
        self.startup()

class WebsiteFrontendRenderer(BaseFrontendRenderer):
    FILE_OUTPUT = BaseFrontendRenderer.DATA_PATH + '/framarama.html'
    TEMPLATE = """<html>
  <head>
    <title>framaRAMA - {{item['title']}}</title>
    <script type="text/javascript">
      const delay = 60000;
      function reload() {
        fetch(window.location.href, {method: 'HEAD'}).then(r => {
          if (String(r.status).startsWith(2) || String(r.status).startsWith(3)) {
            window.location.reload();
          }
        });
        window.setTimeout(() => reload(), delay);
      }
      window.setTimeout(() => reload(), delay);
    </script>
  </head>
  <body>
    <img src="data:{{item['mime']}};base64,{{item['data']}}" style="width: 100%; height: 100%; object-fit: contain;"/>
  </body>
</html>
"""

    def _update(self, title, mime, data):
        _context = context.Context()
        _context.set_resolver('item', context.MapResolver({
            'title': title,
            'mime': mime,
            'data': base64.b64encode(data).decode() if data else ''
        }))
        _content = _context.evaluate(self.TEMPLATE)
        Filesystem.file_write(self.FILE_OUTPUT, str(_content).encode())

    def activate(self, item):
        self._update(item.item().url, item.mime(), item.data())
