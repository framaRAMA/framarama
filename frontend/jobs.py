import datetime
import subprocess
import logging

from django.conf import settings
from django.utils import timezone

from framarama.base import utils
from framarama.base import frontend
from framarama.base.api import ApiClient


logger = logging.getLogger(__name__)


class Jobs():
    FE_INIT = 'fe_init'
    FE_NEXT_ITEM = 'fe_next_item'
    FE_REFRESH_ITEM = 'fe_refresh_items'
    FE_ACTIVATE_ITEM = 'fe_activate_item'
    FE_SUBMIT_STATUS = 'fe_submit_status'
    FE_APP_CHECK = 'fe_app_check'
    FE_APP_UPDATE = 'fe_app_update'

    def __init__(self, scheduler):
        self._display = None
        self._items = None
        self._startup = None
        self._last_update = None
        self._scheduler = scheduler
        self._monitor = None
        if 'frontend' in settings.FRAMARAMA['MODES']:
            self._scheduler.add(self.tick, 'interval', seconds=5, id=Jobs.FE_INIT, name='Frontend timer')
            self._monitor = frontend.Frontend.get().get_device().monitor()
            self._monitor.register_key_event(['Control_R', 'r'], self.key_restart)
            self._monitor.register_key_event(['Control_L', 'r'], self.key_restart)
            self._monitor.register_key_event(['Control_R', 's'], self.key_shutdown)
            self._monitor.register_key_event(['Control_L', 's'], self.key_shutdown)
            self._monitor.register_key_event(['Control_R', 'a'], self.key_network_toggle)
            self._monitor.register_key_event(['Control_L', 'a'], self.key_network_toggle)
            self._monitor.start()

    def _setup_start(self):
        if self._startup is None:
            self._startup = timezone.now()
            _config = frontend.Frontend.get().get_config()
            _config.get_config().date_app_startup = timezone.now()
            _config.get_config().save()
        for _job_name in [Jobs.FE_NEXT_ITEM, Jobs.FE_REFRESH_ITEM, Jobs.FE_SUBMIT_STATUS]:
            if self._scheduler.get(_job_name):
                self._scheduler.remove(_job_name)
    
    def _setup_completed(self):
        if not self._scheduler.get(Jobs.FE_REFRESH_ITEM):
            self._scheduler.add(self.refresh_items, 'interval', minutes=15, id=Jobs.FE_REFRESH_ITEM, name='Frontend refresh items')
        if not self._scheduler.get(Jobs.FE_NEXT_ITEM):
            self._scheduler.add(self.next_item, 'interval', minutes=1, id=Jobs.FE_NEXT_ITEM, name='Frontend next item')
        if not self._scheduler.get(Jobs.FE_SUBMIT_STATUS):
            self._scheduler.add(self.submit_status, 'interval', minutes=5, id=Jobs.FE_SUBMIT_STATUS, name='Frontend status submission')
        self.refresh_items()
        self._scheduler.trigger(Jobs.FE_NEXT_ITEM)
        self._scheduler.trigger(Jobs.FE_SUBMIT_STATUS)

    def key_restart(self):
        logger.info("Restart application!")
        frontend.Frontend.get().get_device().run_capability(frontend.FrontendCapability.APP_RESTART)

    def key_shutdown(self):
        logger.info("Shutdown device!")
        frontend.Frontend.get().get_device().run_capability(frontend.FrontendCapability.APP_SHUTDOWN)

    def key_network_toggle(self):
        logger.info("Toggle network mode!")
        frontend.Frontend.get().get_device().network_ap_toggle()

    def refresh_items(self):
        _display = frontend.Frontend.get().get_display()
        if _display:
            logger.info("Refreshing items ...")
            self._display = _display
            self._items = _display.get_items(True)
            logger.info("Have {} items in list.".format(self._items.count()))
            _config = frontend.Frontend.get().get_config()
            _config.get_config().date_items_update = timezone.now()
            _config.get_config().count_items = self._items.count()
            _config.get_config().save()

    def next_item(self, force=False):
        if self._display is None:
            return
        _now = timezone.now()
        _device = frontend.Frontend.get().get_device()
        _time_on_reached = self._display.time_on_reached(_now)
        _time_off_reached = self._display.time_off_reached(_now)
        _display_on = _device.run_capability(frontend.FrontendCapability.DISPLAY_STATUS)
        if _time_on_reached or _time_off_reached:
            if _time_off_reached:
                if _display_on:
                    logger.info("Switch display off at {}".format(self._display.get_time_off()))
                    _device.run_capability(frontend.FrontendCapability.DISPLAY_OFF)
                    _display_on = False
            elif _time_on_reached:
                if not _display_on:
                    logger.info("Switch display on at {}".format(self._display.get_time_on()))
                    _device.run_capability(frontend.FrontendCapability.DISPLAY_ON)
                    _display_on = True
        if not _display_on and not force:
            logger.info("Skipping next item, display is off.")
        elif self._display.time_change_reached(self._last_update) or force:
            _last_update = self._last_update
            _config = frontend.Frontend.get().get_config().get_config()
            try:
                self._last_update = timezone.now()
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

