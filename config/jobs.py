import logging

from django.conf import settings
from django.db.models import Q, F, functions

from framarama import jobs
from framarama.base import utils
from config import models
from config.utils import source as source_util, finishing

logger = logging.getLogger(__name__)


class Scheduler(jobs.Scheduler):
    CFG_SOURCE_UPDATE = 'cfg_source_update'
    CFG_ITEM_THUMBNAIL = 'cfg_item_thumbnail'

    def configure(self):
        self.register_job(Scheduler.CFG_SOURCE_UPDATE, self.source_update, minutes=1, name='Config source updates')
        self.register_job(Scheduler.CFG_ITEM_THUMBNAIL, self.item_thumbnail, manually=True, name='Generate item thumbnail')
        self.enable_jobs()
        self.trigger_job(Scheduler.CFG_SOURCE_UPDATE)

    def source_update(self, frame=None, source=None):
        _ignored = Q(id__gt=0)
        _enabled_frame = Q(frame__enabled=True)
        _enabled_display = Q(frame__display__enabled=True) | Q(frame__display=None)
        _specific_frame = Q(frame=frame) if frame else _ignored
        _specific_source = Q(pk=source.id) if source else _ignored
        _update_frame_disabled = Q(update_interval__isnull=True)
        _update_frame_defaults = Q(update_interval=utils.DateTime.delta(0))
        _update_frame_initially = Q(update_date_start__isnull=True)
        _update_frame_required = Q(update_date_start__lt=utils.DateTime.now()-F('update_interval'))

        if frame is None and source is None:
            _interval = utils.DateTime.delta(settings.FRAMARAMA['CONFIG_SOURCE_UPDATE_INTERVAL'])
            if _interval is None:
                return
            _update_initial = ~_update_frame_disabled & _update_frame_initially
            _update_by_interval = ~_update_frame_disabled & ~_update_frame_defaults & _update_frame_required
            _update_by_source_interval = _update_initial | _update_by_interval
            _update_by_global_interval = _update_frame_defaults & Q(update_date_start__lt=functions.Now()-_interval)
        else:
            _update_by_source_interval = _ignored
            _update_by_global_interval = _ignored

        _criteria = (
          _enabled_frame &
          _enabled_display &
          _specific_frame &
          _specific_source &
          (_update_by_source_interval | _update_by_global_interval)
        )

        for _source in models.Source.objects.filter(_criteria).order_by('-update_date_start'):
            _frame = _source.frame
            _job_id = Scheduler.CFG_SOURCE_UPDATE
            if self.running_jobs(_job_id, instance=_frame.id, starts_with=True) > 1:
                logger.info('Skipping update {} {} - already running for frame'.format(_frame, _source))
            else:
                logger.info("Updating {} {}".format(_frame, _source))
                self.run_job(_job_id, self.run_source_update, instance=[_frame.id, _source.id], name='Updating {} {}'.format(_frame, _source), func_kwargs={'source': _source})
                break

    def run_source_update(self, source):
        _variables = {}
        for _setting in models.Settings.objects.filter(user=source.frame.user, category=models.Settings.CAT_VARS):
            _variables.update({_setting.name: _setting.properties})
        _processor = source_util.Processor(source_util.Context(source.frame, source, _variables))
        _processor.process()

    def item_thumbnail(self, item):
        logger.info("Generating thumbnail for {}".format(item))
        _size = settings.FRAMARAMA['CONFIG_THUMBNAIL_SIZE']
        _adapter = finishing.ImageProcessingAdapter.get_default()
        _image = _adapter.image_open(item.url)
        _adapter.image_resize(_image, _size[0], _size[1], True)
        logger.info("Result: {}".format(_image))
        _data = _adapter.image_data(_image)
        _meta = _adapter.image_meta(_image)
        _thumbnail = models.ItemThumbnailData.create(data=_data, mime=_meta['mime'])
        if item.thumbnail:
            item.thumbnail.update(_thumbnail)
        else:
            item.thumbnail = _thumbnail
        item.thumbnail.save()
        item.save()

