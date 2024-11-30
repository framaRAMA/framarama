import logging

from django.apps import apps
from django.shortcuts import render
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.db.models import F

from framarama.base import utils, api
from framarama.base.views import BaseAuthenticatedView
from config import forms, models, plugins


logger = logging.getLogger(__name__)


class BaseConfigView(BaseAuthenticatedView):
    DEFAULT_THUMBNAIL = utils.Filesystem.file_read('common/static/common/fontawesome-free-6.1.1-web/svgs/regular/image.svg')
    DEFAULT_THUMBNAIL_MIME = 'image/svg+xml'

    def __init__(self):
        self._config = utils.Config.get()

    def get_config(self):
        return self._config.get_config() if self._config else None

    def get_scheduler(self):
        return apps.get_app_config('config').get_scheduler()

    def get_frames(self):
        return self.qs().frames

    def get_displays(self):
        return self.qs().displays

    def _tz(self, context):
        if self.request.user and self.request.user.time_zone:
            return self.request.user.time_zone
        return super()._tz(context)

    def _get(self, request):
        _context = {}
        _context['config'] = self.get_config()
        _context['frames'] = self.get_frames()
        _context['displays'] = self.get_displays()
        return _context

    def response_item_thumbnail(self, context, item):
        _thumbnail_data = BaseConfigView.DEFAULT_THUMBNAIL
        _thumbnail_mime = BaseConfigView.DEFAULT_THUMBNAIL_MIME
        try:
            if item and item.thumbnail:
                _thumbnail_data = item.thumbnail.data()
                _thumbnail_mime = item.thumbnail.data_mime
        except Exception as e:
            logger.error("Can not load thumbnail data #{}: {}".format(data.thumbnail.id, e))
        self.response(context, _thumbnail_data, _thumbnail_mime)

    def response_item_download(self, context, item):
        _download_data = BaseConfigView.DEFAULT_THUMBNAIL
        _download_mime = BaseConfigView.DEFAULT_THUMBNAIL_MIME
        try:
            if item and item.url:
                _response = api.ApiClient.get().get_url(item.url)
                _response.raise_for_status()
                _download_data = _response.content
                _download_mime = _response.headers['content-type']
        except Exception as e:
            logger.error("Can not load item data #{}: {}".format(item.id, e))
        self.response(context, _download_data, _download_mime)


class BaseFrameConfigView(BaseConfigView):

    def _item_order_delete(self, pk, items):
        item = items.filter(pk=pk).get()
        item.delete();
        items.filter(ordering__gt=item.ordering).update(ordering=F('ordering')-1)

    def _item_order_move(self, action, item, items, target=None):
        if items.is_tree():
            if action in ['up', 'down']:
                _target = item.get_prev_sibling() if action == 'up' else item.get_next_sibling()
                _pos = 'left' if action == 'up' else 'right'
            elif action in ['up-out', 'down-in']:
                _target = item.get_parent() if action == 'up-out' else item.get_next_sibling()
                _pos = 'left' if action == 'up-out' else 'first-child'
            elif action in ['move-after', 'move-before'] and target:
                _target = items.get(pk=target)
                _pos = 'left' if action == 'move-before' else 'right'
            elif action in ['first-child'] and target:
                _target = items.get(pk=target)
                _pos = 'first-child'
            if _target and not _target.is_root():
                logger.info("Move {} to {} of {}".format(item, _pos, _target))
                item.move(_target, _pos)
        else:
            _ordering = item.ordering
            _ordering_target = _ordering-1 if action == 'up' else _ordering+1
            _item_other = items.filter(ordering=_ordering_target).first()
            if _item_other:
                _item_other.ordering = _ordering
                _item_other.save()
                item.ordering = _ordering_target
                item.save()

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _context['frame'] = self.get_frames().get(id=frame_id)
        return _context

    def _post(self, request, frame_id, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _context['frame'] = self.get_frames().get(id=frame_id)
        return _context

    def redirect_finishing_list(self, context, finishing, *args, **kwargs):
        self.redirect(context, 'frame_finishing_list', query='open={}'.format(finishing.id), *args, **kwargs)


class BaseSourceFrameConfigView(BaseFrameConfigView):

    def _get(self, request, frame_id, source_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _sources = list(_frame.sources.all())
        _source = [source for source in _sources if source.id == source_id][0]
        _context['sources'] = _sources
        _context['source'] = _source
        _context['steps'] = _source.steps.all()
        return _context


class BaseStepSourceFrameConfigView(BaseSourceFrameConfigView):

    def _get(self, request, frame_id, source_id, step_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _context['source_step'] = _context['source'].steps.get(pk=step_id)
        _context['plugin'] = plugins.SourcePluginRegistry.get(_context['source_step'].plugin)
        return _context

    def _post(self, request, frame_id, source_id, step_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _context['source_step'] = _context['source'].steps.get(pk=step_id)
        _context['plugin'] = plugins.SourcePluginRegistry.get(_context['source_step'].plugin)
        return _context


class BaseSortingFrameConfigView(BaseFrameConfigView):

    def _get(self, request, frame_id, sorting_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _sorting = _frame.sortings.get(pk=sorting_id)
        _context['sorting'] = _sorting
        return _context

    def _post(self, request, frame_id, sorting_id, *args, **kwargs):
        _context = super()._post(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _sorting = _frame.sortings.get(pk=sorting_id)
        _context['sorting'] = _sorting
        return _context


class BaseFinishingFrameConfigView(BaseFrameConfigView):

    def _get(self, request, frame_id, finishing_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _finishing = _frame.finishings.get(pk=finishing_id)
        _context['finishing'] = _finishing
        return _context


class BaseContextFrameConfigView(BaseFrameConfigView):

    def _get(self, request, frame_id, context_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _frame_context = _frame.contexts.get(pk=context_id)
        _context['context'] = _frame_context
        return _context


class BaseDisplayConfigView(BaseConfigView):

    def _get(self, request, display_id, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _context['display'] = self.qs().displays.get(id=display_id)
        return _context



