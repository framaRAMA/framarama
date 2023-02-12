import datetime
import zoneinfo
import subprocess
import logging

from django.utils import timezone

from framarama import settings, jobs
from framarama.base import utils
from framarama.base import frontend, device
from framarama.base.api import ApiClient


logger = logging.getLogger(__name__)


class Scheduler(jobs.Scheduler):
    FE_INIT = 'fe_init'
    FE_REFRESH_DISPLAY = 'fe_refresh_display'
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
        self._monitor = None
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
        self.add_job(Scheduler.FE_INIT, self.tick, seconds=5, name='Frontend timer')

    def _setup_start(self):
        if self._startup is None:
            self._startup = utils.DateTime.now()
            _config = frontend.Frontend.get().get_config()
            _config.get_config().date_app_startup = utils.DateTime.now()
            _config.get_config().save()
        self.disable_jobs()
    
    def _setup_completed(self):
        self.refresh_display()
        self.refresh_items()
        self.timezone_activate()
        self.enable_jobs()
        self.trigger_job(Scheduler.FE_NEXT_ITEM)
        self.trigger_job(Scheduler.FE_SUBMIT_STATUS)

    def timezone_activate(self):
        _time_zone = frontend.Frontend.get().get_config().get_config().sys_time_zone
        _time_zone = _time_zone if _time_zone else settings.TIME_ZONE
        logger.info("Using time zone {}".format(_time_zone))
        timezone.activate(zoneinfo.ZoneInfo(_time_zone))

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
        _time_on_reached = self._display.time_on_reached()
        _time_off_reached = self._display.time_off_reached()
        _display_on = _device.get_capability().display_status()
        if _time_on_reached or _time_off_reached:
            if _time_off_reached:
                if _display_on:
                    logger.info("Switch display off at {}".format(self._display.get_time_off()))
                    _device.get_capability().display_off()
                    _display_on = False
            elif _time_on_reached:
                if not _display_on:
                    logger.info("Switch display on at {}".format(self._display.get_time_on()))
                    _device.get_capability().display_on()
                    _display_on = True
        _device = frontend.Frontend.get().get_device()
        if self._last_update is None and len(_device.get_files()):
            logger.info("Last items exist, activating the last one.")
            self._last_update = utils.DateTime.now()
            _device.activate(0)
        elif not _display_on and not force:
            logger.info("Skipping next item, display is off.")
        elif not self._display.get_enabled():
            logger.info("Skipping next item, display is not enabled.")
        elif self._display.time_change_reached(self._last_update) or force:
            _last_update = self._last_update
            _config = frontend.Frontend.get().get_config().get_config()
            try:
                self._last_update = utils.DateTime.now()
                logger.info("Retrieve next item ...")
                _next_item = self._display.get_next_item(True)
                logger.info("Next item is {}".format(_next_item))
                _finishings = self._display.get_finishings(True)
                _frontend_item = _device.finish(self._display, _next_item, _finishings)
                _device.render(self._display, _frontend_item)
                logger.info("Image updated ({} bytes, {}x{} pixels, mime {})!".format(
                    len(_frontend_item.data()),
                    _frontend_item.width(),
                    _frontend_item.height(),
                    _frontend_item.mime()))
                _config.count_views = _config.count_views + 1
            except Exception as e:
                self._last_update = _last_update
                _config.count_errors = _config.count_errors + 1
                raise
            finally:
                _config.save()
            self._display.submit_item_hit(_frontend_item)

    def submit_status(self):
        if self._display is None:
            return
        frontend.Frontend.get().submit_status()

    def tick(self):
        _frontend = frontend.Frontend.get()
        _network = _frontend.get_device().network_verify()
        if not _frontend.initialize() or not _frontend.api_access():
            self._setup_start()
        elif _network and (self._display is None or self._items is None):
            self._setup_completed()
        elif not _network:
            self._setup_start()

