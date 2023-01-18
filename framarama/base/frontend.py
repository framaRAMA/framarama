import os
import io
import re
import time
import fcntl
import threading
import datetime
import jsonpickle
import urllib
import logging

from django.conf import settings
from django.core import management
from django.contrib.auth.models import User
from django.db import connections

from frontend import models
from framarama.base import device
from framarama.base.utils import Singleton, Config, Filesystem, Process, DateTime
from framarama.base.api import ApiClient, ApiResultItem
from config.utils import finishing
from config import models as config_models


logger = logging.getLogger(__name__)


class Frontend(Singleton):
    INIT_PHASE_START = 0
    INIT_PHASE_DB_DEFAULT = 1   # Check if frontend/default DB is available
    INIT_PHASE_CONFIGURED = 2   # Frontend configuration exists
    INIT_PHASE_DB_CONFIG = 3    # Check if config DB is available
    INIT_PHASE_SETUP = 4        # Setup configured
    INIT_PHASE_API_ACCESS = 5   # API access possible

    def __init__(self):
        super().__init__()
        self._client = None
        self._init_phase = Frontend.INIT_PHASE_START

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
        if self._init_phase < Frontend.INIT_PHASE_CONFIGURED:
            _configs = list(models.Config.objects.all())
            if len(_configs) == 0:
                logger.info("Creating default configuration")
                _config = models.Config()
                _config.save()
                _configs.append(_config)
                Singleton.clear()
            self._init_phase = Frontend.INIT_PHASE_CONFIGURED
        if self._init_phase < Frontend.INIT_PHASE_DB_CONFIG:
            self._init_admin_user()
            if 'config' in connections:
                self._init_migrations('config')
            else:
                logger.info("Skipping migration of config because default is used")
            self._init_phase = Frontend.INIT_PHASE_DB_CONFIG
        if self._init_phase < Frontend.INIT_PHASE_SETUP:
            _mode = self.get_config().get_config().mode
            if _mode != None and _mode.strip() != '':
                self._init_phase = Frontend.INIT_PHASE_SETUP
        if self.is_setup() and not self.api_access():
            _client = ApiClient.get()
            if _client.configured():
                self._client = _client
                self._init_phase = Frontend.INIT_PHASE_API_ACCESS
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

    def get_status(self):
        _config = self.get_config().get_config()
        _device = self.get_device()
        _capability = _device.get_capability()
        _uptime = _capability.sys_uptime()
        _mem_total = _capability.mem_total()
        _mem_free = _capability.mem_free()
        _cpu_load = _capability.cpu_load()
        _cpu_temp = _capability.cpu_temp()
        _disk_data = _capability.disk_data_free()
        _disk_tmp = _capability.disk_tmp_free()
        _network_config = _capability.net_config()
        _network_status = _device.network_status()
        _app_revision = _capability.app_revision()
        _files = _device.get_files()
        _latest_items = [{
            'id': _files[_name]['json']['item'].id,
            'time': DateTime.utc(_files[_name]['json']['time'])
        } for _name in _files]
        _data = {
            'uptime': _uptime,
            'memory': {
                'used': _mem_total - _mem_free if _mem_total and _mem_free else None,
                'free': _mem_free if _mem_free else None,
            },
            'cpu': {
                'load': _cpu_load,
                'temp': _cpu_temp,
            },
            'disk': {
                'data': {
                    'used': _disk_data[0],
                    'free': _disk_data[1],
                },
                'tmp': {
                    'used': _disk_tmp[0],
                    'free': _disk_tmp[1],
                },
            },
            'network': {
                'profile': _network_status['profile'],
                'connected': DateTime.utc(_network_status['connected']) if _network_status['connected'] else None,
                'address': {
                    'ip': _network_config['ip'] if _network_config else None,
                    'gateway': _network_config['gateway'] if _network_config else None,
                }
            },
            'screen': self.get_screen(),
            'items': {
                'total': _config.count_items,
                'shown': _config.count_views,
                'error': _config.count_errors,
                'updated': DateTime.utc(_config.date_items_update) if _config.date_items_update else None,
                'latest': _latest_items,
            },
            'app': {
                'date': DateTime.utc(_app_revision['date']) if _app_revision else None,
                'hash': _app_revision['hash'] if _app_revision else None,
                'branch': _app_revision['branch'] if _app_revision else None,
                'revision': _app_revision['current'] if _app_revision else None,
            },
        }
        return _data

    def submit_status(self):
        _display = self.get_display()
        _data = self.get_status()
        logger.info("Submitting status information: {}".format(_data))
        try:
            self._client.submit_status(_display.get_id(), _data)
        except Exception as e:
            logger.warning("Could not submit status information: {}".format(e))


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

    def get_next_item(self, refresh=False, hit=True):
        if self._next is None or refresh:
            self._next = self._client.get_items_next(self.get_id(), hit)
        return self._next

    def get_finishings(self, refresh=False):
        if self._finishings is None or refresh:
            self._finishings = self._client.get_finishings(self.get_id())
        return self._finishings


class FrontendDevice(Singleton):

    def __init__(self):
        super().__init__()
        self._monitor = FrontendMonitoring()
        self._network = {'started': None, 'connected': None, 'profile': None, 'previous': None, 'networks': None}
        self._renderer_filesystem = FilesystemFrontendRenderer()
        self._renderer_visualization = VisualizeFrontendRenderer()
        self._renderers = [
            DefaultFrontendRenderer(),
            self._renderer_filesystem,
            self._renderer_visualization,
        ]
        self._capability = None

    def monitor(self):
        return self._monitor

    def finish(self, display, item, finishings):
        _capability = self.get_capability()
        _mem_total = _capability.mem_total()
        _mem_free = _capability.mem_free()
        _mem_max = round(1024 * _mem_free * 0.8)
        logger.info("Restricting memory usage to {:.0f} MB".format(_mem_max/1024/1024))
        _disk_free_tmp = _capability.disk_tmp_free()
        _disk_free_tmp_max = round(1024 * _disk_free_tmp[1] * 0.8)
        logger.info("Restricting disk usage to {:.0f} MB".format(_disk_free_tmp_max/1024/1024))
        _adapter = finishing.WandImageProcessingAdapter()
        _adapter._wand_resource.limits['memory'] = _mem_max
        _adapter._wand_resource.limits['disk'] = _disk_free_tmp_max
        _context = finishing.Context(
            display.display(),
            display.frame(),
            item,
            finishings.items(),
            _adapter)
        with _context:
            _config = Frontend.get().get_config().get_config()
            _processor = finishing.Processor(_context)
            _processor.set_watermark(_config.watermark_type, _config.watermark_scale, _config.watermark_scale)
            _result = _processor.process()
            return FrontendItem(item, _result)

    def render(self, display, item):
        for renderer in self._renderers:
            renderer.process(display, item)

    def activate(self, item):
        self._renderer_filesystem.activate(item)
        self._renderer_visualization.startup()

    def get_files(self):
        return self._renderer_filesystem.files()

    def network_connect(self, name):
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
        _ap_active = device.Capabilities.nmcli_ap_active(_profile_list)
        if self._network['started'] is None:
            self._network['started'] = DateTime.now()
            logger.info("Checking network connectivity ...")
            if _ap_active:
                logger.info("Access Point active - disabling first!")
                self.network_ap_toggle()
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
                else:
                    logger.info("Not connected within 30 seconds - try to connect previous network {}".format(_previous))
                    self._network['profile'] = None
                    self._network['previous'] = None
                    self.network_connect(_previous)
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
            logger.info("Connected to {}".format(self._network['profile']))
            return True
        return False

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

    def __init__(self, item, result):
        self._item = item
        self._result = result

    def item(self):
        return self._item

    def data(self):
        return self._result.get_data()

    def preview(self):
        return self._result.get_preview()

    def mime(self):
        return self._result.get_mime()

    def width(self):
        return self._result.get_width()

    def height(self):
        return self._result.get_height()


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
    FILE_CURRENT = 'framarama-current.image'

    def _file(self, file_name):
        return self.FILE_PATH + '/' + file_name

    def process(self, display, item):
        _config = Frontend.get().get_config().get_config()
        _files = Filesystem.file_rotate(
            self.FILE_PATH,
            self.FILE_PATTERN,
            self.FILE_FORMAT,
            _config.count_items_keep if _config.count_items_keep else 6,
            ['json', 'image', 'preview'])

        _json = jsonpickle.encode({
          'item': item.item(),
          'mime': item.mime(),
          'time': datetime.datetime.utcnow()
        })

        Filesystem.file_write(_files['json'], _json.encode())
        Filesystem.file_write(_files['image'], item.data())
        Filesystem.file_write(_files['preview'], item.preview())
        self.activate(0)

    def activate(self, item):
        _item = int(item)
        _files = list(self.files().values())
        if _item >=0 and _item < len(_files):
            Filesystem.file_copy(_files[_item]['image_file'], self.FILE_PATH + '/' + self.FILE_CURRENT)

    def files(self):
        _files = {}
        for (_file, _num, _ext) in Filesystem.file_match(self.FILE_PATH, self.FILE_PATTERN):
            _file_json = self._file(_file)
            _file_image = self._file(self.FILE_FORMAT.format(int(_num), 'image'))
            _file_preview = self._file(self.FILE_FORMAT.format(int(_num), 'preview'))
            _files[_file] = {
                'json': jsonpickle.decode(Filesystem.file_read(_file_json)),
                'image': Filesystem.file_read(_file_image),
                'image_file': _file_image,
                'preview': Filesystem.file_read(_file_preview),
                'preview_file': _file_preview,
            }
        return _files


class VisualizeFrontendRenderer(BaseFrontendRenderer):
    DATA_PATH = settings.FRAMARAMA['DATA_PATH']
    COMMON_PATH = settings.FRAMARAMA['COMMON_PATH']
    IMG_CURRENT = DATA_PATH + '/framarama-current.image'
    FILE_LIST = DATA_PATH + '/framarama-current.csv'

    CMD_FEH = ['feh', '--fullscreen', '--auto-zoom', '--stretch', '--auto-rotate', '--scale-down', '-bg-fill', DATA_PATH + '/picture-background.jpg', '-f', DATA_PATH + '/picture-current.csv', '--reload', '10']
    CMD_IMAGICK = ['magick', 'display', '-window', 'root']

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
        _file_list = VisualizeFrontendRenderer.FILE_LIST
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
            Filesystem.file_write(_file_list, VisualizeFrontendRenderer.IMG_CURRENT.encode())
    
    def update_magic(self):
        Process.exec_run(self.CMD_IMAGICK + [VisualizeFrontendRenderer.IMG_CURRENT])

    def process(self, display, item):
        self.startup()

