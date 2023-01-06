import logging

from django.conf import settings

from framarama.base import utils
from config import models
from config.utils import source as source_util

logger = logging.getLogger(__name__)


class Jobs():
    CFG_SOURCE_UPDATE = 'cfg_source_update'

    def __init__(self, scheduler):
        self._scheduler = scheduler
        if 'server' in settings.FRAMARAMA['MODES']:
            self._scheduler.add(self.source_update, 'interval', minutes=1, id=Jobs.CFG_SOURCE_UPDATE, name='Config source updates')
        self._scheduler.trigger(Jobs.CFG_SOURCE_UPDATE)

    def source_update(self, frame=None, source=None):
        _prev_update = utils.DateTime.now() - utils.DateTime.delta(settings.FRAMARAMA['CONFIG_SOURCE_UPDATE_INTERVAL'])
        _sources = models.Source.objects.filter(
            update_date_start__lt=_prev_update,
            frame__enabled=True,
            frame__display__enabled=True)
        if frame:
            _sources = _sources.filter(frame=frame)
        if source:
            _sources = _sources.filter(id=source.id)
        for _source in _sources.order_by('-update_date_start'):
            _frame = _source.frame
            _job_id = Jobs.CFG_SOURCE_UPDATE + '_' + str(_frame.id)
            if self._scheduler.running(_job_id, True):
                logger.info('Skipping update {} {} - already running for frame'.format(_frame, _source))
            else:
                logger.info("Updating {} {}".format(_frame, _source))
                self._scheduler.add(self.run_source_update, id=_job_id + '_' + str(_source.id), func_kwargs={'source': _source})
                break

    def run_source_update(self, source):
        _processor = source_util.Processor(source_util.Context(source.frame, source))
        _processor.process()

