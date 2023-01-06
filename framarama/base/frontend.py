import os
import io
import re
import time
import fcntl
import threading
import datetime
import jsonpickle
import ipaddress
import urllib
import logging

from django.conf import settings
from django.core import management
from django.utils import dateparse
from django.contrib.auth.models import User

from frontend import models
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

    def get_screen(self):
        _device = self.get_device()
        _display_status = _device.run_capability(FrontendCapability.DISPLAY_STATUS)
        _display_size = _device.run_capability(FrontendCapability.DISPLAY_SIZE)
        return {
            'on': _display_status,
            'width': _display_size[0] if _display_size else None,
            'height': _display_size[1] if _display_size else None,
        }

    def get_status(self):
        _config = self.get_config().get_config()
        _display = self.get_display()
        _device = self.get_device()
        _uptime = _device.run_capability(FrontendCapability.SYS_UPTIME)
        _mem_total = _device.run_capability(FrontendCapability.MEM_TOTAL)
        _mem_free = _device.run_capability(FrontendCapability.MEM_FREE)
        _cpu_load = _device.run_capability(FrontendCapability.CPU_LOAD)
        _cpu_temp = _device.run_capability(FrontendCapability.CPU_TEMP)
        _disk_data_free = _device.run_capability(FrontendCapability.DISK_DATA_FREE)
        _disk_tmp_free = _device.run_capability(FrontendCapability.DISK_TMP_FREE)
        _network_config = _device.run_capability(FrontendCapability.NET_CONFIG)
        _network_status = _device.network_status()
        _app_revision = _device.run_capability(FrontendCapability.APP_REVISION)
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
                    'used': None,
                    'free': _disk_data_free,
                },
                'tmp': {
                    'used': None,
                    'free': _disk_tmp_free,
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

    def time_on_reached(self, time):
        _time_on = DateTime.delta(self.get_time_on())
        if _time_on:
            _midnight = DateTime.midnight()
            return _midnight + _time_on < time
        return False

    def get_time_off(self):
        return self._data.item().time_off

    def time_off_reached(self, time):
        _time_off = DateTime.delta(self.get_time_off())
        if _time_off:
            _midnight = DateTime.midnight()
            return _midnight + _time_off < time
        return False

    def get_time_change(self):
        return DateTime.delta(
            self._data.get('time_change', '00:05:00'))

    def time_change_reached(self, last_update):
        _now = DateTime.now()
        _time_change = self.get_time_change()
        return last_update is None or last_update + _time_change < _now

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
        self._capabilities = None

    def monitor(self):
        return self._monitor

    def finish(self, display, item, finishings):
        _mem_total = self.run_capability(FrontendCapability.MEM_TOTAL)
        _mem_free = self.run_capability(FrontendCapability.MEM_FREE)
        _mem_max = round(1024 * _mem_free * 0.8)
        logger.info("Restricting memory usage to {:.0f} MB".format(_mem_max/1024/1024))
        _disk_free_tmp = self.run_capability(FrontendCapability.DISK_TMP_FREE)
        _disk_free_tmp_max = round(1024 * _disk_free_tmp * 0.8)
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
        self.run_capability(FrontendCapability.NET_PROFILE_CONNECT, name=name)
        self._network['started'] = None
        self._network['connected'] = None
        self._network['previous'] = self._network['profile']
        self._network['profile'] = name
        self._network['networks'] = None

    def network_status(self):
        return self._network

    def network_ap_toggle(self):
        self.run_capability(FrontendCapability.NET_TOGGLE_AP)

    def network_verify(self):
        if self._network['connected']:
            return True
        _profile_list = self.run_capability(FrontendCapability.NET_PROFILE_LIST)
        _ap_active = FrontendCapability.nmcli_ap_active(_profile_list)
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
                    self._network['networks'] = self.run_capability(FrontendCapability.NET_WIFI_LIST)
                    self.network_ap_toggle()
                    self._network['connected'] = DateTime.now()
                else:
                    logger.info("Not connected within 30 seconds - try to connect previous network {}".format(_previous))
                    self._network['profile'] = None
                    self._network['previous'] = None
                    self.network_connect(_previous)
            else:
                _ip = self.run_capability(FrontendCapability.NET_CONFIG)
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

    def get_capabilities(self):
        if self._capabilities is None:
            self._capabilities = {
                FrontendCapability.DISPLAY_ON: FrontendCapability.noop,
                FrontendCapability.DISPLAY_OFF: FrontendCapability.noop,
                FrontendCapability.DISPLAY_STATUS: FrontendCapability.return_true,
                FrontendCapability.DISPLAY_SIZE: FrontendCapability.return_none,
                FrontendCapability.MEM_TOTAL: FrontendCapability.return_none,
                FrontendCapability.MEM_FREE: FrontendCapability.return_none,
                FrontendCapability.SYS_UPTIME: FrontendCapability.return_none,
                FrontendCapability.CPU_TEMP: FrontendCapability.return_none,
                FrontendCapability.CPU_LOAD: FrontendCapability.return_none,
                FrontendCapability.DISK_DATA_FREE: FrontendCapability.return_none,
                FrontendCapability.DISK_TMP_FREE: FrontendCapability.return_none,
                FrontendCapability.NET_CONFIG: FrontendCapability.return_none,
                FrontendCapability.NET_TOGGLE_AP: FrontendCapability.return_none,
                FrontendCapability.NET_WIFI_LIST: FrontendCapability.return_dict,
                FrontendCapability.NET_PROFILE_LIST: FrontendCapability.return_list,
                FrontendCapability.NET_PROFILE_SAVE: FrontendCapability.return_none,
                FrontendCapability.NET_PROFILE_DELETE: FrontendCapability.return_none,
                FrontendCapability.APP_LOG: FrontendCapability.return_none,
                FrontendCapability.APP_RESTART: FrontendCapability.return_none,
                FrontendCapability.APP_SHUTDOWN: FrontendCapability.return_none,
                FrontendCapability.APP_REVISION: FrontendCapability.return_none,
                FrontendCapability.APP_CHECK: FrontendCapability.return_none,
                FrontendCapability.APP_UPDATE: FrontendCapability.return_none,
            }
            if Process.exec_search('vcgencmd'):  # Raspberry PIs
                self._capabilities[FrontendCapability.DISPLAY_ON] = FrontendCapability.vcgencmd_display_on
                self._capabilities[FrontendCapability.DISPLAY_OFF] = FrontendCapability.vcgencmd_display_off
                self._capabilities[FrontendCapability.DISPLAY_STATUS] = FrontendCapability.vcgencmd_display_status
            elif Process.exec_search('xrandr'):
                self._capabilities[FrontendCapability.DISPLAY_ON] = FrontendCapability.xrandr_display_on
                self._capabilities[FrontendCapability.DISPLAY_OFF] = FrontendCapability.xrandr_display_off
                self._capabilities[FrontendCapability.DISPLAY_STATUS] = FrontendCapability.xrandr_display_status
            if Process.exec_search('xrandr'):
                self._capabilities[FrontendCapability.DISPLAY_SIZE] = FrontendCapability.xrandr_display_size
            if Filesystem.file_exists('/proc/meminfo'):
                self._capabilities[FrontendCapability.MEM_TOTAL] = FrontendCapability.read_meminfo_total
                self._capabilities[FrontendCapability.MEM_FREE] = FrontendCapability.read_meminfo_free
            if Filesystem.file_exists('/proc/uptime'):
                self._capabilities[FrontendCapability.SYS_UPTIME] = FrontendCapability.read_uptime
            if Process.exec_search('uptime'):
                self._capabilities[FrontendCapability.CPU_LOAD] = FrontendCapability.uptime_loadavg
            if Filesystem.file_exists('/sys/class/thermal/thermal_zone0/temp'):
                self._capabilities[FrontendCapability.CPU_TEMP] = FrontendCapability.read_thermal
            if Process.exec_search('df'):
                self._capabilities[FrontendCapability.DISK_DATA_FREE] = FrontendCapability.df_data
                self._capabilities[FrontendCapability.DISK_TMP_FREE] = FrontendCapability.df_tmp
            if Process.exec_search('ip'):
                self._capabilities[FrontendCapability.NET_CONFIG] = FrontendCapability.ip_netcfg
            if Process.exec_search('nmcli'):
                self._capabilities[FrontendCapability.NET_TOGGLE_AP] = FrontendCapability.nmcli_toggle_ap
                self._capabilities[FrontendCapability.NET_WIFI_LIST] = FrontendCapability.nmcli_wifi_list
                self._capabilities[FrontendCapability.NET_PROFILE_LIST] = FrontendCapability.nmcli_profile_list
                self._capabilities[FrontendCapability.NET_PROFILE_SAVE] = FrontendCapability.nmcli_profile_save
                self._capabilities[FrontendCapability.NET_PROFILE_DELETE] = FrontendCapability.nmcli_profile_delete
                self._capabilities[FrontendCapability.NET_PROFILE_CONNECT] = FrontendCapability.nmcli_profile_connect
            if Process.exec_run(['sudo', '-n', 'systemctl', 'show', 'framarama'], sudo=True):
                self._capabilities[FrontendCapability.APP_LOG] = FrontendCapability.app_log_systemd
                self._capabilities[FrontendCapability.APP_RESTART] = FrontendCapability.app_restart_systemd
            if Process.exec_search('shutdown'):
                self._capabilities[FrontendCapability.APP_SHUTDOWN] = FrontendCapability.app_shutdown
            if Process.exec_search('git'):
                self._capabilities[FrontendCapability.APP_REVISION] = FrontendCapability.app_revision
                self._capabilities[FrontendCapability.APP_CHECK] = FrontendCapability.app_check
                self._capabilities[FrontendCapability.APP_UPDATE] = FrontendCapability.app_update

        return self._capabilities

    def run_capability(self, capability, *args, **kwargs):
        _capabilities = self.get_capabilities()
        if capability in _capabilities:
            return _capabilities[capability](self, *args, **kwargs)


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


class FrontendCapability:
    DISPLAY_OFF = 'display.off'
    DISPLAY_ON = 'display.on'
    DISPLAY_STATUS = 'display.status'
    DISPLAY_SIZE = 'display.size'
    MEM_TOTAL = 'memory.total'
    MEM_FREE = 'memory.free'
    DISK_DATA_FREE = 'disk.data.free'
    DISK_TMP_FREE = 'disk.tmp.free'
    SYS_UPTIME = 'system.uptime'
    CPU_LOAD = 'cpu.load'
    CPU_TEMP = 'cpu.temp'
    NET_CONFIG = 'network.config'
    NET_TOGGLE_AP = 'network.toggle.ap'
    NET_WIFI_LIST = 'network.wifi.list'
    NET_PROFILE_LIST = 'network.profile.list'
    NET_PROFILE_SAVE = 'network.profile.save'
    NET_PROFILE_DELETE = 'network.profile.delete'
    NET_PROFILE_CONNECT = 'network.profile.connect'
    APP_LOG = 'app.log'
    APP_RESTART = 'app.restart'
    APP_SHUTDOWN = 'app.shutdown'
    APP_REVISION = 'app.revision'
    APP_CHECK = 'app.check'
    APP_UPDATE = 'app.update'

    def noop(device, *args, **kwargs):
        return

    def return_false(device, *args, **kwargs):
        return False

    def return_true(device, *args, **kwargs):
        return True

    def return_none(device, *args, **kwargs):
        return None

    def return_list(device, *args, **kwargs):
        return []

    def return_dict(device, *args, **kwargs):
        return {}

    def vcgencmd_display_on(device, *args, **kwargs):
        Process.exec_run(['vcgencmd', 'display_power', '1'])

    def vcgencmd_display_off(device, *args, **kwargs):
        Process.exec_run(['vcgencmd', 'display_power', '0'])

    def vcgencmd_display_status(device, *args, **kwargs):
        return Process.exec_run(['vcgencmd', 'display_power']) == b'display_power=1\n'

    def _xrandr_display_name():
        _name = None
        _status = True
        _xrandr = Process.exec_run(['xrandr'])
        if _xrandr:
            _lines = _xrandr.split(b'\n')
            # HDMI-1 connected primary 1280x800+0+0 (normal left inverted right x axis y axis) 337mm x 270mm
            _connected = [_line for _line in _lines if b'connected' in _line]
            if len(_connected):
                _name = _connected[0].split(b' ')[0]
            #    1280x800      59.81*+
            _size = [_line for _line in _lines if b'x' in _line and b'.' in _line]
            if len(_size):
                _status = len([_line for _line in _size if b'*' in _line]) > 0
        return (_name, _status)

    def xrandr_display_on(device, *args, **kwargs):
        (_name, _status) = FrontendCapability._xrandr_display_name()
        if _name:
            Process.exec_run(['xrandr', '--output', _name, '--auto'])

    def xrandr_display_off(device, *args, **kwargs):
        (_name, _status) = FrontendCapability._xrandr_display_name()
        if _name:
            Process.exec_run(['xrandr', '--output', _name, '--off'])

    def xrandr_display_status(device, *args, **kwargs):
        (_name, _status) = FrontendCapability._xrandr_display_name()
        return _status

    def xrandr_display_size(device, *args, **kwargs):
        _xrandr = Process.exec_run(['xrandr'])
        if _xrandr:
            # Screen 0: minimum 320 x 200, current 1920 x 1080, maximum 16384 x 16384
            for _resolution in _xrandr.split(b'\n')[0].split(b','):
                if b'current' in _resolution:
                    _values = _resolution.strip().split(b' ')
                    return (int(_values[1]), int(_values[3]))
        return None

    def _read_meminfo(fields=None):
        _lines = Filesystem.file_read('/proc/meminfo')
        _lines = [_line for _line in _lines.split(b'\n') if _line] if _lines else []
        _lines = [_line.split() for _line in _lines]
        _info = {_line[0].decode().strip(':'): _line[1].decode() for _line in _lines}
        if fields:
            return tuple([_info.get(_field) for _field in fields])
        else:
            return _info

    def read_meminfo_total(device, *args, **kwargs):
        _mem_total, = FrontendCapability._read_meminfo(['MemTotal'])
        return int(_mem_total) if _mem_total else None

    def read_meminfo_free(device, *args, **kwargs):
        _mem_free, _mem_cached = FrontendCapability._read_meminfo(['MemFree', 'Cached'])
        return int(_mem_free) + int(_mem_cached) if _mem_free else None

    def read_uptime(device, *args, **kwargs):
        _info = Filesystem.file_read('/proc/uptime')
        return float(_info.split(b'.')[0]) if _info else None

    def _df(partition):
        _info = Process.exec_run(['df', '-k', partition])
        return int(_info.split()[-3]) if _info else None

    def df_data(device, *args, **kwargs):
        return FrontendCapability._df(settings.FRAMARAMA['DATA_PATH'])

    def df_tmp(device, *args, **kwargs):
        return FrontendCapability._df('/tmp')

    def uptime_loadavg(device, *args, **kwargs):
        _info = Process.exec_run(['uptime'])
        return float(_info.split()[-3].rstrip(b',')) if _info else None

    def read_thermal(device, *args, **kwargs):
        _info = Filesystem.file_read('/sys/class/thermal/thermal_zone0/temp')
        return int(float(_info)/1000) if _info else None

    def ip_netcfg(device, *args, **kwargs):
        _info = Process.exec_run(['ip', 'route'])
        _info = [_line.decode() for _line in _info.split(b'\n') if _line.startswith(b'default via')] if _info else []
        _info = [_line.split() for _line in _info][0] if _info else None
        _gateway = _info[2] if _info and len(_info) > 1 else None
        _device = _info[4] if _info and len(_info) > 3 else None
        _dhcp = (_info[6] == 'dhcp') if _info and len(_info) > 5 else None

        _info = Process.exec_run(['ip', 'a', 'show', 'dev', _device]) if _device else ''
        _info = [_line.decode().split() for _line in _info.split(b'\n')] if _info else []
        _mac = None
        _ipv4 = []
        _ipv6 = []
        for _line in [_line for _line in _info if _line]:
            if _line[0].startswith('link'):
                _mac = _line[1]
            elif _line[0] == 'inet':
                _ipv4.append(_line[1])
            elif _line[0] == 'inet6':
                _ipv6.append(_line[1])
        _gw_ip = ipaddress.ip_address(_gateway) if _gateway else None
        _ip = [_ip.split('/')[0] for _ip in _ipv4 + _ipv6 if _gw_ip in ipaddress.ip_network(_ip, strict=False)]

        return {
            'gateway': _gateway,
            'device': _device,
            'mac': _mac,
            'ip': _ip,
            'ipv4': _ipv4,
            'ipv6': _ipv6,
            'mode': 'DHCP' if _dhcp else 'static'
        }

    def nmcli_profile_list(device, *args, **kwargs):
        _profiles = {}
        # NAME       UUID                                  TYPE  DEVICE  ACTIVE
        # NetName1   93dba0ab-4cd6-4c0f-b790-2c5689f8686b  wifi  wlan0   yes
        # NetName2   909c4d81-4211-4810-9f98-32f74f43906a  wifi  --      no
        _profile_list = Process.exec_run(['nmcli', '--fields', 'NAME,UUID,TYPE,DEVICE,ACTIVE', 'connection', 'show'])
        if _profile_list:
            _profile_list = _profile_list.decode().split('\n')
            _columns = _profile_list.pop(0).lower().split()
            for _parts in [_line.split() for _line in _profile_list]:
                if len(_parts) == 0:
                    continue
                _i = 0
                _profile = {}
                for _column in _columns:
                    _value = _parts[_i]
                    if _column == 'active':
                        _value = True if _value == 'yes' else False
                    _profile[_column] = _value
                    _i = _i + 1
                _profiles[_profile['name']] = _profile
        return _profiles

    def nmcli_ap_active(profiles):
        return 'framarama' in profiles and profiles['framarama']['active']

    def nmcli_profile_save(device, name, password, *args, **kwargs):
        if name is None or name == '' or password is None or password == '':
            return
        _profiles = FrontendCapability.nmcli_profile_list(device, *args, **kwargs)
        _args = ['sudo', 'nmcli', 'connection']
        if name in _profiles:
            _args.extend(['modify', name])
            _args.extend(['802-11-wireless-security.psk', password])
            logger.info("Updating network {}".format(name))
        else:
            _args.extend(['add'])
            _args.extend(['connection.id', name])
            _args.extend(['connection.type', '802-11-wireless'])
            _args.extend(['connection.autoconnect', '1'])
            _args.extend(['802-11-wireless.ssid', name])
            _args.extend(['802-11-wireless-security.key-mgmt', 'wpa-psk'])
            _args.extend(['802-11-wireless-security.psk', password])
            logger.info("Adding network {}".format(name))
        Process.exec_run(_args, sudo=True)

    def nmcli_profile_delete(device, name, *args, **kwargs):
        if name is None or name == '':
            return
        _profiles = FrontendCapability.nmcli_profile_list(device, *args, **kwargs)
        if name not in _profiles or _profiles[name]['active']:
            return
        logger.info("Deleting network {}".format(name))
        Process.exec_run(['sudo', 'nmcli', 'connection', 'delete', name], sudo=True)

    def nmcli_profile_connect(device, name, *args, **kwargs):
        if name is None or name == '':
            return
        _profiles = FrontendCapability.nmcli_profile_list(device, *args, **kwargs)
        if name not in _profiles:
            return
        _wifi_list = FrontendCapability.nmcli_wifi_list(device, *args, **kwargs)
        if name not in _wifi_list:
            return
        logger.info("Connecting network {}".format(name))
        Process.exec_run(['sudo', 'nmcli', 'connection', 'up', name], sudo=True)

    def nmcli_wifi_list(device, *args, **kwargs):
        _networks = {}
        # IN-USE  BSSID              SSID          MODE   CHAN  RATE        SIGNAL  BARS  SECURITY
        # *       XX:XX:XX:XX:XX:XX  NetworkName   Infra  6     130 Mbit/s  46      ▂▄__  WPA1 WPA2
        _wifi_list = Process.exec_run(['sudo', 'nmcli', 'device', 'wifi', 'list', '--rescan', 'yes'], sudo=True)
        if _wifi_list:
            _wifi_list = _wifi_list.decode().split('\n')
            _columns = _wifi_list.pop(0).lower().split()
            for _parts in [_line.split() for _line in _wifi_list]:
                if len(_parts) == 0:
                    continue
                _network = {'active': _parts[0] == '*'}
                if _network['active']:
                    _parts.pop(0)
                _i = 0
                for _column in _columns:
                    if 'use' in _column:  # skip in-use column, already checked
                        continue
                    elif 'rate' in _column:
                        _network[_column] = _parts[_i] + ' ' + _parts[_i+1]
                        _i = _i + 1
                    else:
                        _network[_column] = _parts[_i]
                    _i = _i + 1
                if _network['ssid'] != 'framaRAMA':
                    _networks[_network['ssid']] = _network
        return _networks

    def nmcli_toggle_ap(device, *args, **kwargs):
        _profiles = FrontendCapability.nmcli_profile_list(device, *args, **kwargs)
        if not FrontendCapability.nmcli_ap_active(_profiles):
            logger.info("Activating Access Point.")
            if 'framarama' not in _profiles:
                Process.exec_run(['sudo', '-n', 'nmcli', 'device', 'wifi', 'hotspot', 'con-name', 'framarama', 'ssid', 'framaRAMA', 'password', 'framarama', 'band', 'bg'], sudo=True)
            else:
                Process.exec_run(['sudo', '-n', 'nmcli', 'connection', 'up', 'framarama'], sudo=True)
        else:
            logger.info("Deactivating Access Point.")
            Process.exec_run(['sudo', '-n', 'nmcli', 'connection', 'delete', 'framarama'], sudo=True)

    def app_log_systemd(device, *args, **kwargs):
        return Process.exec_run(['sudo', '-n', 'systemctl', 'status', '-n', '100', 'framarama'], sudo=True)

    def app_restart_systemd(device, *args, **kwargs):
        return Process.exec_run(['sudo', '-n', 'systemctl', 'restart', 'framarama'], sudo=True)

    def app_shutdown(device, *args, **kwargs):
        return Process.exec_run(['sudo', 'shutdown', '-h', 'now'], sudo=True)

    def _git_remotes():
        _remotes = Process.exec_run(['git', 'remote', '-v'])
        _remotes = [_line.split() for _line in _remotes.decode().split('\n') if len(_line)] if _remotes else []
        _remotes = {_parts[0]: _parts[1] for _parts in _remotes if _parts[-1] == '(fetch)'}
        return _remotes

    def _git_revisions():
        _revisions = []
        _out = Process.exec_run(['git', 'branch', '-r'])
        if _out:
            _out = [_line.strip() for _line in _out.decode().split('\n')]
            _revisions.extend(_out)
        _out = Process.exec_run(['git', 'tag', '-l'])
        if _out:
            _out = [_line for _line in _out.decode().split('\n')]
            _revisions.extend(_out)
        return [_rev for _rev in _revisions if len(_rev)]

    def app_revision(device, *args, **kwargs):
        _log = Process.exec_run(['git', 'log', '-1', '--pretty=format:%h %aI %s'])
        # de4a83b 2022-12-17T11:14:06+01:00 Implement frontend capability to retrieve display size (using xrandr)
        if _log:
            _values = _log.decode().split(' ')
            _branch = Process.exec_run(['git', 'branch', '--show-current'])
            _branch = _branch.decode().strip() if _branch else None
            _rev = {
                'hash': _values[0],
                'date': dateparse.parse_datetime(_values[1]),
                'comment': _values[2],
                'branch': _branch,
                'remotes': FrontendCapability._git_remotes(),
                'revisions': FrontendCapability._git_revisions(),
            }
            return _rev
        return None

    def app_check(device, remote, url, username, password, *args, **kwargs):
        _url = re.sub(r'^(.*://)([^@]+@)?(.*)', '\\1' + re.escape(username) + '@\\3', url)
        logger.info("Check version update from {} using {} ...".format(remote, _url))
        _remotes = FrontendCapability._git_remotes()
        if remote in _remotes:
            logger.info("Update remote {} to {}".format(remote, _url))
            _remote_update = Process.exec_run(['git', 'remote', 'set-url', remote, _url])
        else:
            logger.info("Adding remote {} to {}".format(name, _url))
            _remote_update = Process.exec_run(['git', 'remote', 'add', name, _url])
        if _remote_update is None:
            logger.error("Can not setup remote {} with {}".format(name, _url))
            return
        _fetch = Process.exec_run(['git', 'fetch', remote], env={
            'GIT_ASKPASS': settings.BASE_DIR / 'docs' / 'git' / 'git-ask-pass.sh' ,
            'GIT_PASSWORD': password,
        })
        if _fetch is None:
            logger.error("Can not fetch updates!")
        else:
            logger.info("Updates fetched!")
        Process.exec_run(['git', 'remote', 'set-url', remote, url])

    def app_update(device, revision, *args, **kwargs):
        logger.info("Check version update ...")
        _revisions = FrontendCapability._git_revisions()
        if revision not in _revisions:
            logger.error("Can not update to non-existant revision {}".format(revision))
            return
        _stash = Process.exec_run(['git', 'stash'])
        if _stash is None:
            logger.error("Can not stash changes!")
            return
        logger.info("Changes stashed!")
        _pull = Process.exec_run(['git', 'checkout', revision])
        if _pull is None:
            logger.error("Can checkout revision!")
        else:
            logger.info("Revision checked out!")
        _pop = Process.exec_run(['git', 'stash', 'pop'])
        if _pop is None:
            logger.error("Can pop stash again!")


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

