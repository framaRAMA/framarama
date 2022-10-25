import datetime
import subprocess
import logging

from django.utils import timezone

from framarama.base import utils
from framarama.base.utils import ApiClient


logger = logging.getLogger(__name__)


class Jobs():

    def __init__(self, scheduler):
        self._display = None
        self._items = None
        self._startup = None
        self._last_update = None
        self._scheduler = scheduler
        self._scheduler.add(self.tick, 'interval', seconds=5, id='fe_init', name='Frontend timer')

    def _setup_start(self):
        if self._startup is None:
            self._startup = timezone.now()
            _config = utils.Frontend.get().get_config()
            _config.get_config().date_app_startup = timezone.now()
            _config.get_config().save()
        for _job_name in ['fe_next_time', 'fe_refresh_items']:
            if self._scheduler.get(_job_name):
                self._scheduler.remove(_job_name)
    
    def _setup_completed(self):
        if not self._scheduler.get('fe_refresh_items'):
            self._scheduler.add(self.refresh_items, 'interval', minutes=15, id='fe_refresh_items', name='Frontend refresh items')
        if not self._scheduler.get('fe_next_item'):
            self._scheduler.add(self.next_item, 'interval', minutes=5, id='fe_next_item', name='Frontend next item')
        self.refresh_items()
        self.next_item()

    def refresh_items(self):
        _display = utils.Frontend.get().get_display()
        if _display:
            print("Refreshing items ...")
            self._display = _display
            self._items = _display.get_items()
            print("Have {} items in list.".format(self._items.count()))
            _config = utils.Frontend.get().get_config()
            _config.get_config().date_items_update = timezone.now()
            _config.get_config().count_items = self._items.count()
            _config.get_config().save()

    def next_item(self):
        if self._display and self._display.time_change_reached(self._last_update):
            self._last_update = timezone.now()
            print("Retrieve next item ...")
            _next_item = self._display.get_next_item(True)
            print("Next item is {}".format(_next_item))
            _finishings = self._display.get_finishings()
            _device = utils.Frontend.get().get_device()
            _frontend_item = _device.finish(self._display, _next_item, _finishings)
            _device.render(self._display, _frontend_item)
            print("Image updated ({} bytes, {}x{} pixels, mime {})!".format(
                len(_frontend_item.data()),
                _frontend_item.width(),
                _frontend_item.height(),
                _frontend_item.mime()))
            _config = utils.Frontend.get().get_config()
            _config.get_config().count_views = _config.get_config().count_views + 1
            _config.get_config().save()

    def tick(self):
        if not utils.Frontend.get().initialize() or not utils.Frontend.get().api_access():
            self._setup_start()
        elif self._display is None or self._items is None:
            self._setup_completed()

