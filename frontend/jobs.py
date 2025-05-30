import os
import datetime
import zoneinfo
import subprocess
import logging

from apscheduler.triggers.cron import CronTrigger

from django.utils import timezone

from framarama import settings, jobs
from framarama.base import utils
from framarama.base import frontend, device
from framarama.base.api import ApiClient


logger = logging.getLogger(__name__)


class Scheduler(jobs.Scheduler):
    FE_INIT = 'fe_init'
    FE_REFRESH_DISPLAY = 'fe_refresh_display'
    FE_DISPLAY_ON = 'fe_display_on'
    FE_DISPLAY_OFF = 'fe_display_off'
    FE_NEXT_ITEM = 'fe_next_item'
    FE_REFRESH_ITEM = 'fe_refresh_items'
    FE_ACTIVATE_ITEM = 'fe_activate_item'
    FE_SUBMIT_STATUS = 'fe_submit_status'
    FE_APP_CHECK = 'fe_app_check'
    FE_APP_UPDATE = 'fe_app_update'
    FE_DEVICE_RESTART = 'fe_device_restart'
    FE_DEVICE_SHUTDOWN = 'fe_device_shutdown'
    FE_WIFI_CONNECT = 'fe_wifi_connect'
    FE_WIFI_AP = 'fe_wifi_ap'

    def configure(self):
        self._display = None
        self._items = None
        self._startup = None
        self._last_update = None
        self._time_zone = None
        self._stream = None
        if settings.FRAMARAMA['FRONTEND_KEYSTROKES']:
            logger.info("Registering frontend keystrokes")
            self._monitor = frontend.Frontend.get().get_device().monitor()
            self._monitor.register_key_event(['Control_R', 'r'], self.key_restart)
            self._monitor.register_key_event(['Control_L', 'r'], self.key_restart)
            self._monitor.register_key_event(['Control_R', 's'], self.key_shutdown)
            self._monitor.register_key_event(['Control_L', 's'], self.key_shutdown)
            self._monitor.register_key_event(['Control_R', 'a'], self.key_network_toggle)
            self._monitor.register_key_event(['Control_L', 'a'], self.key_network_toggle)
            self._monitor.start()
        self.register_job(Scheduler.FE_REFRESH_DISPLAY, self.refresh_display, minutes=10, name='Frontend refresh display')
        self.register_job(Scheduler.FE_NEXT_ITEM, self.next_item, minutes=1, name='Frontend next item')
        self.register_job(Scheduler.FE_REFRESH_ITEM, self.refresh_items, minutes=15, name='Frontend refresh items')
        self.register_job(Scheduler.FE_SUBMIT_STATUS, self.submit_status, minutes=5, name='Frontend status submission')
        self.register_job(Scheduler.FE_APP_CHECK, self.app_check, hours=1, minutes=15, name='Frontend update check')
        self.register_job(Scheduler.FE_APP_UPDATE, self.app_update, hours=1, minutes=30, name='Frontend update install')
        self.add_job(Scheduler.FE_INIT, self.tick, seconds=5, name='Frontend timer')

    def _setup_start(self):
        if self._startup is None:
            _config = frontend.Frontend.get().get_config().get_config()
            if _config is None:
                return
            self._startup = utils.DateTime.now()
            _config.date_app_startup = self._startup
            _config.save()
        self.disable_jobs()
    
    def _setup_completed(self):
        self.timezone_activate()
        self.refresh_display()
        self.refresh_items()
        self.enable_jobs()
        self.trigger_job(Scheduler.FE_NEXT_ITEM)
        self.trigger_job(Scheduler.FE_SUBMIT_STATUS)

    def _scan_mount_paths(self):
        _media_path = settings.FRAMARAMA['MEDIA_PATH']
        _mount_path = settings.FRAMARAMA['MOUNT_PATH']
        _mount_level = settings.FRAMARAMA['MOUNT_LEVEL']
        if not utils.Filesystem.path_exists(_mount_path):
            return
        if not utils.Filesystem.path_exists(_media_path):
            utils.Filesystem.path_create(_media_path)
        _links = [(os.path.basename(_mount[0]), _mount[0]) for _mount in utils.Filesystem.file_match(
            _media_path, '.*', files=False, links=True)] if _media_path else []
        _mounts = [(os.path.basename(_link[0]), _link[0]) for _link in utils.Filesystem.file_match(
            _mount_path, '.*', files=False, dirs=True,
            recurse=_mount_level, recurse_min=_mount_level)] if _mount_path else []
        utils.Lists.process(
            _mounts, lambda ids: [(_name, _path) for _name, _path in _links if _name in ids],
            _links, lambda ids: [(_name, _path) for _name, _path in _mounts if _name in ids],
            create_func=lambda name, path: logger.info("Adding mount path {} -> {}".format(
                _mount_path + '/' + path,
                _media_path + '/' + name,
                utils.Filesystem.file_link(_mount_path + '/' + path, _media_path + '/' + name))),
            delete_func=lambda name, path: logger.info("Removing mount path {}".format(
                _media_path + '/' + name,
                utils.Filesystem.file_delete(_media_path + '/' + name))))

    def timezone_activate(self):
        self._time_zone = frontend.Frontend.get().get_config().get_config().sys_time_zone
        self._time_zone = self._time_zone if self._time_zone else settings.TIME_ZONE
        logger.info("Scheduler timezone is {}".format(self._time_zone))

    def key_restart(self):
        logger.info("Restart application!")
        frontend.Frontend.get().get_device().get_capability().app_restart()

    def key_shutdown(self):
        logger.info("Shutdown device!")
        frontend.Frontend.get().get_device().get_capability().app_shutdown()

    def key_network_toggle(self):
        logger.info("Toggle network mode!")
        frontend.Frontend.get().get_device().network_ap_toggle()

    def refresh_display(self):
        logger.info("Updating display ...")
        self._display = frontend.Frontend.get().get_display(force=True)
        _jobs = {
            Scheduler.FE_DISPLAY_ON: (self._display.get_time_on(), self.display_on, 'Frontend display on'),
            Scheduler.FE_DISPLAY_OFF: (self._display.get_time_off(), self.display_off, 'Frontend display off'),
        }
        _schedules = {}
        for _job, _conf in _jobs.items():
            self.disable_job(_job)
            if _conf[0]:
                logger.info("Register job {} at {}".format(_job, _conf[0]))
                _target = utils.DateTime.get(utils.DateTime.midnight(tz=self._time_zone), add=_conf[0])
                _trigger = CronTrigger(year="*", month="*", day="*", hour=_target.hour, minute=_target.minute, second="0")
                self.register_job(_job, _conf[1], trigger=_trigger, name=_conf[2])
                self.enable_job(_job)
                _schedules[_job] = utils.DateTime.delta(_conf[0])
        if Scheduler.FE_DISPLAY_OFF == utils.DateTime.in_range(utils.DateTime.midnight(tz=self._time_zone), _schedules):
            self.display_off()
        else:
            self.display_on()

    def display_on(self):
        _device = frontend.Frontend.get().get_device()
        _status = _device.display_toggle(True)
        if _status is not None and _status:
            logger.info("Switch display on at {}".format(self._display.get_time_on()))

    def display_off(self):
        _device = frontend.Frontend.get().get_device()
        _status = _device.display_toggle(False)
        if _status is not None and not _status:
            logger.info("Switch display off at {}".format(self._display.get_time_off()))

    def refresh_items(self):
        if self._display:
            logger.info("Refreshing items ...")
            self._items = self._display.get_items(True)
            logger.info("Have {} items in list.".format(self._items.count()))
            _config = frontend.Frontend.get().get_config()
            _config.get_config().date_items_update = utils.DateTime.now()
            _config.get_config().count_items = self._items.count()
            _config.get_config().save()

    def next_item(self, force=False):
        if self._display is None:
            return
        _device = frontend.Frontend.get().get_device()
        _display_on = _device.get_capability().display_status()
        if self._last_update is None and len(_device.get_items()):
            logger.info("Last items exist, activating the last one.")
            self._last_update = utils.DateTime.now()
            _device.activate(0)
        elif not _display_on and not force:
            logger.info("Skipping next item, display is off.")
        elif not self._display.get_enabled():
            logger.info("Skipping next item, display is not enabled.")
        elif self._stream is not None:
            _stream_items = _device.get_streamed()
            if len(_stream_items) and _stream_items[0].time() > self._stream:
                _stream_idle = _stream_items[0].time()
            else:
                _stream_idle = self._stream
            _stream_idle = int((utils.DateTime.now() - _stream_idle).total_seconds()/60)
            logger.info("Skipping next item, streaming enabled (idle {:d} minutes)".format(_stream_idle))
        elif self._display.time_change_reached(self._last_update) or force:
            _last_update = self._last_update
            _config = frontend.Frontend.get().get_config().get_config()
            _restrictions = _config.cloud_status_restriction
            try:
                self._last_update = utils.DateTime.now()
                logger.info("Retrieve next item ...")
                _next_item = self._display.get_next_item(True)
                logger.info("Next item is {}".format(_next_item))
                _frontend_item = _device.finish_item(self._display, _next_item)
                _device.activate(0)
                _config.count_views = _config.count_views + 1
            except Exception as e:
                self._last_update = _last_update
                _config.count_errors = _config.count_errors + 1
                raise
            finally:
                _config.save()
            self._display.submit_item_hit(_frontend_item, 'thumbs' in _restrictions if _restrictions else False)

    def stream_toggle(self):
        self._stream = utils.DateTime.now() if self._stream is None else None

    def is_streaming(self):
        return self._stream

    def submit_status(self):
        if self._display is None:
            return
        frontend.Frontend.get().submit_status()

    def app_check(self, url=None, username=None, password=None, force=False):
        _config = frontend.Frontend.get().get_config().get_config()
        if _config.app_update_check is None:
            _interval = utils.DateTime.delta(settings.FRAMARAMA['FRONTEND_APP_UPDATE_INTERVAL'])
        elif _config.app_update_check is utils.DateTime.delta(0):
            _interval = None
        else:
            _interval = _config.app_update_check
        if force is False:
            if _interval is None:
                return
            if not utils.DateTime.reached(_config.app_update_check_date, _interval):
                return
        _capability = frontend.Frontend.get().get_device().get_capability()
        _config.app_update_check_date = utils.DateTime.now()
        _config.app_update_check_status = 'Checking for updates...'
        _config.save()
        _config.app_update_check_status = _capability.app_check(url=url, username=username, password=password)
        _config.save()

    def app_update(self, revision=None, force=False):
        _frontend = frontend.Frontend.get()
        _config = _frontend.get_config().get_config()
        if force is False and _config.app_update_install is not None and _config.app_update_install is False:
            return
        if _config.app_update_install_hour is not None:
            _diff = utils.DateTime.midnight()-utils.DateTime.now(sub=_config.app_update_install_hour)
        else:
            _diff = 0
        if force is False and _diff and (_diff < 0 or _diff > 2*60*60):
            return
        _capability = frontend.Frontend.get().get_device().get_capability()
        _config.app_update_install_status = 'Update in progress...'
        _config.save()
        _app_update = _capability.app_update(revision=revision)
        if type(_app_update) == bool:
            _config.app_update_install_status = None
        else:
            _config.app_update_install_status = _app_update
        if _app_update == True:
            _config.app_update_install_date = utils.DateTime.now()
            _frontend.init_set(None)
        if _app_update == False:
            _config.app_update_install_status = None
        _config.save()
        if _app_update == True:
            _capability.app_restart()

    def tick(self):
        _frontend = frontend.Frontend.get()
        _network = _frontend.get_device().network_verify()
        if not _frontend.is_initialized() or not _frontend.api_access():
            self._setup_start()
            self._display = None
            self._items = None
        elif not _network:
            self._setup_start()
        elif self._display is None or self._items is None:
            self._setup_completed()
        else:
            self._scan_mount_paths()
        _frontend.initialize()

