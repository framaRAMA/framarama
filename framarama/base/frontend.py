import io
import datetime
import jsonpickle
import logging

from django.conf import settings
from django.core import management
from django.utils import timezone
from django.contrib.auth.models import User

from frontend import models
from framarama.base.utils import Singleton, Config, Filesystem, Process
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


class Display(Singleton):

    def __init__(self):
        super().__init__()
        self._client = ApiClient.get()
        self._data = self._client.get_display()
        self._items = None
        self._next = None
        self._finishings = None

    def _time_delta(self, time_str):
        if time_str is None:
            return None
        _time = datetime.time.fromisoformat(time_str)
        return datetime.timedelta(hours=_time.hour, minutes=_time.minute)

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
        _time_on = self._time_delta(self.get_time_on())
        if _time_on:
            _midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return _midnight + _time_on < time
        return False

    def get_time_off(self):
        return self._data.item().time_off

    def time_off_reached(self, time):
        _time_off = self._time_delta(self.get_time_off())
        if _time_off:
            _midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return _midnight + _time_off < time
        return False

    def get_time_change(self):
        return self._time_delta(self._data.get('time_change', '00:05:00'))

    def time_change_reached(self, last_update):
        _now = timezone.now()
        _time_change = self.get_time_change()
        return last_update is None or last_update + _time_change < _now

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
        ]
        self._capabilities = None

    def finish(self, display, item, finishings):
        return self._finisher.process(display, item, finishings)

    def render(self, display, item):
        for renderer in self._renderers:
            renderer.process(display, item)

    def get_files(self):
        return self._renderer_filesystem.files()

    def get_capabilities(self):
        if self._capabilities is None:
            self._capabilities = {
                FrontendCapability.DISPLAY_ON: FrontendCapability.noop,
                FrontendCapability.DISPLAY_OFF: FrontendCapability.noop,
                FrontendCapability.DISPLAY_STATUS: FrontendCapability.return_true,
            }
            if Process.exec_search('vcgencmd'):  # Raspberry PIs
                self._capabilities[FrontendCapability.DISPLAY_ON] = FrontendCapability.vcgencmd_display_on
                self._capabilities[FrontendCapability.DISPLAY_OFF] = FrontendCapability.vcgencmd_display_off
                self._capabilities[FrontendCapability.DISPLAY_STATUS] = FrontendCapability.vcgencmd_display_status
        return self._capabilities

    def run_capability(self, capability, *args, **kwargs):
        _capabilities = self.get_capabilities()
        if capability in _capabilities:
            return _capabilities[capability](self, *args, **kwargs)


class FrontendCapability:
    DISPLAY_OFF = 'display.off'
    DISPLAY_ON = 'display.on'
    DISPLAY_STATUS = 'display.status'

    def noop(device, *args, **kwargs):
        return

    def return_false(device, *args, **kwargs):
        return False

    def return_true(device, *args, **kwargs):
        return True

    def vcgencmd_display_on(device, *args, **kwargs):
        Process.exec_run(['vcgencmd', 'display_power', '1'])

    def vcgencmd_display_off(device, *args, **kwargs):
        Process.exec_run(['vcgencmd', 'display_power', '0'])

    def vcgencmd_display_status(device, *args, **kwargs):
        return Process.exec_run(['vcgencmd', 'display_power']) == '1'

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
    IMG_CURRENT = DATA_PATH + '/framarama-00001.image'

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

    def update_feh(self, display, item):
        _background = VisualizeFrontendRenderer.DATA_PATH + '/framarama-background.jpg'
        _file_list = VisualizeFrontendRenderer.DATA_PATH + '/framarama-current.csv'
        if Process.exec_running('feh') is None:
            Process.exec_bg([
                'feh',
                '--fullscreen',
                '--auto-zoom',
                '--stretch',
                '--auto-rotate',
                '--scale-down',
                '-bg-fill', _background,
                '-f', _file_list,
                '--reload', '10'
            ])
        if not Filesystem.file_exists(_file_list) or Filesystem.file_size(_file_list) == 0:
            Filesystem.file_write(_file_list, VisualizeFrontendRenderer.IMG_CURRENT.encode())
    
    def update_magic(self, display, item):
        Process.exec_run(self.CMD_IMAGICK + [VisualizeFrontendRenderer.IMG_CURRENT])

    def process(self, display, item):
        if self._update == None:
            self.discover()
        if self._update == None:
            return
        self._update(display, item)


