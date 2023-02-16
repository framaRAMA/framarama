import logging

from django.conf import settings
from django.db.models import Q

from framarama import jobs
from framarama.base import utils
from config import models
from config.utils import source as source_util

logger = logging.getLogger(__name__)


class Scheduler(jobs.Scheduler):
    CFG_SOURCE_UPDATE = 'cfg_source_update'

    def configure(self):
        self.register_job(Scheduler.CFG_SOURCE_UPDATE, self.source_update, minutes=1, name='Config source updates')
        self.enable_jobs()
        self.trigger_job(Scheduler.CFG_SOURCE_UPDATE)

    def source_update(self, frame=None, source=None):
        _criteria = Q(frame__enabled=True)
        _criteria.add(Q(frame__display__enabled=True) | Q(frame__display=None), Q.AND)
        if frame:
            _criteria.add(Q(frame=frame), Q.AND)
        if source:
            _criteria.add(Q(id=source.id), Q.AND)
        if frame is None and source is None:
            _interval = utils.DateTime.delta(settings.FRAMARAMA['CONFIG_SOURCE_UPDATE_INTERVAL'])
            if _interval is None:
                return
            _prev_update = utils.DateTime.now(sub=_interval)
            _criteria.add(Q(update_date_start__lt=_prev_update), Q.AND)
        for _source in models.Source.objects.filter(_criteria).order_by('-update_date_start'):
            _frame = _source.frame
            _job_id = Scheduler.CFG_SOURCE_UPDATE + '_' + str(_frame.id)
            if self.running_jobs(_job_id, True) > 1:
                logger.info('Skipping update {} {} - already running for frame'.format(_frame, _source))
            else:
                logger.info("Updating {} {}".format(_frame, _source))
                self.run_job(_job_id + '_' + str(_source.id), self.run_source_update, name='Updating {} {}'.format(_frame, _source), func_kwargs={'source': _source})
                break

    def run_source_update(self, source):
        _processor = source_util.Processor(source_util.Context(source.frame, source))
        _processor.process()

