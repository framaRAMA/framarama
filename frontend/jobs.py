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

    def __init__(self, scheduler):
        self._display = None
        self._items = None
        self._startup = None
        self._last_update = None
        self._scheduler = scheduler
        self._monitor = None
        if 'frontend' in settings.FRAMARAMA['MODES']:
            self._scheduler.add(self.tick, 'interval', seconds=5, id='fe_init', name='Frontend timer')
            self._monitor = frontend.Frontend.get().get_device().monitor()
            self._monitor.register_key_event(['Control_R', 'r'], self.key_restart)
            self._monitor.register_key_event(['Control_L', 'r'], self.key_restart)
            self._monitor.register_key_event(['Control_R', 's'], self.key_shutdown)
            self._monitor.register_key_event(['Control_L', 's'], self.key_shutdown)

    def _setup_start(self):
        if self._monitor:
            self._monitor.stop()
        if self._startup is None:
            self._startup = timezone.now()
            _config = frontend.Frontend.get().get_config()
            _config.get_config().date_app_startup = timezone.now()
            _config.get_config().save()
        for _job_name in ['fe_next_time', 'fe_refresh_items']:
            if self._scheduler.get(_job_name):
                self._scheduler.remove(_job_name)
    
    def _setup_completed(self):
        if self._monitor:
            self._monitor.start()
        if not self._scheduler.get('fe_refresh_items'):
            self._scheduler.add(self.refresh_items, 'interval', minutes=15, id='fe_refresh_items', name='Frontend refresh items')
        if not self._scheduler.get('fe_next_item'):
            self._scheduler.add(self.next_item, 'interval', minutes=1, id='fe_next_item', name='Frontend next item')
        self.refresh_items()
        self.next_item()

    def key_restart(self):
        logger.info("Restart application!")
        frontend.Frontend.get().get_device().run_capability(frontend.FrontendCapability.APP_RESTART)

    def key_shutdown(self):
        logger.info("Shutdown device!")
        frontend.Frontend.get().get_device().run_capability(frontend.FrontendCapability.APP_SHUTDOWN)

    def refresh_items(self):
        _display = frontend.Frontend.get().get_display()
        if _display:
            logger.info("Refreshing items ...")
            self._display = _display
            self._items = _display.get_items()
            logger.info("Have {} items in list.".format(self._items.count()))
            _config = frontend.Frontend.get().get_config()
            _config.get_config().date_items_update = timezone.now()
            _config.get_config().count_items = self._items.count()
            _config.get_config().save()

    def next_item(self):
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
        if not _display_on:
            logger.info("Skipping next item, display is off.")
        elif self._display.time_change_reached(self._last_update):
            _last_update = self._last_update
            try:
                self._last_update = timezone.now()
                logger.info("Retrieve next item ...")
                _next_item = self._display.get_next_item(True)
                logger.info("Next item is {}".format(_next_item))
                _finishings = self._display.get_finishings()
                _frontend_item = _device.finish(self._display, _next_item, _finishings)
                _device.render(self._display, _frontend_item)
                logger.info("Image updated ({} bytes, {}x{} pixels, mime {})!".format(
                    len(_frontend_item.data()),
                    _frontend_item.width(),
                    _frontend_item.height(),
                    _frontend_item.mime()))
                _config = frontend.Frontend.get().get_config()
                _config.get_config().count_views = _config.get_config().count_views + 1
                _config.get_config().save()
            except Exception as e:
                self._last_update = _last_update
                raise

    def tick(self):
        if not frontend.Frontend.get().initialize() or not frontend.Frontend.get().api_access():
            self._setup_start()
        elif self._display is None or self._items is None:
            self._setup_completed()

