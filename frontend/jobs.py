import datetime

from framarama.base import utils


class Jobs():

    def __init__(self, scheduler):
        self._display = None
        self._items = None
        self._last_update = None
        scheduler.add(self.refresh_items, 'interval', minutes=15, id='fe_refresh_items', name='Frontend refresh items')
        scheduler.add(self.next_item, 'interval', minutes=5, id='fe_next_item', name='Frontend next item')
        scheduler.add(self.tick, 'interval', seconds=5, id='fe_tick', name='Frontend timer tick')

    def init(self):
        self.refresh_items()

    def refresh_items(self):
        print("Refreshing items ...")
        _display = utils.Frontend.get().get_display()
        if _display:
            self._display = _display
            self._items = _display.get_items()
            print("Have {} items in list.".format(self._items.count()))

    def next_item(self):
        if self._display.time_change_reached(self._last_update):
            self._last_update = datetime.datetime.utcnow()
            print("Retrieve next item ...")
            _next_item = self._display.get_next_item(True)
            print("Next item is {}".format(_next_item))
            _finishings = self._display.get_finishings()
            _device = utils.Frontend.get().get_device()
            _frontend_item = _device.finish(self._display, _next_item, _finishings)
            _device.render(self._display, _frontend_item)
            print("Image updated ({} bytes, mime {})!".format(len(_frontend_item.data()), _frontend_item.mime()))

    def tick(self):
        if not self._display:  # do initialization stuff
            self.refresh_items()
            self.next_item()

