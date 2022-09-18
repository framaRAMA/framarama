
from django.shortcuts import render
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.db.models import F

from framarama.base.views import BaseAuthenticatedView
from frontend.models import Config
from config import forms
from config import models
from config import plugins


class BaseConfigView(BaseAuthenticatedView):

    def get_config(self):
        _configs = list(Config.objects.all())
        return _configs[0] if len(_configs) else None

    def get_frames(self):
        return models.Frame.objects.filter(user=self.request.user)

    def get_displays(self):
        return models.Display.objects.filter(user=self.request.user)

    def _get(self, request):
        _context = {}
        _context['config'] = self.get_config()
        _context['frames'] = self.get_frames()
        return _context


class BaseFrameConfigView(BaseConfigView):

    def _item_order_delete(self, pk, items):
        item = items.filter(pk=pk).get()
        item.delete();
        items.filter(ordering__gt=item.ordering).update(ordering=F('ordering')-1)

    def _item_order_move(self, action, item, items):
        _ordering = item.ordering
        _ordering_target = _ordering-1 if action == 'up' else _ordering+1
        _item_other_filter = items.filter(ordering=_ordering_target)
        if _item_other_filter.exists():
            _item_other_filter = _item_other_filter.get()
            _item_other_filter.ordering = _ordering
            _item_other_filter.save()
            item.ordering = _ordering_target
            item.save()

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _context['frame'] = self.get_frames().get(id=frame_id)
        return _context


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

    def _get(self, request, frame_id, source_id, plugin, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _context['plugin'] = plugins.SourcePluginRegistry.get(plugin)
        return _context

    def _post(self, request, frame_id, source_id, plugin, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _context['plugin'] = plugins.SourcePluginRegistry.get(plugin)
        return _context


class BaseSortingFrameConfigView(BaseFrameConfigView):

    def _get(self, request, frame_id, sorting_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
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


class BaseDisplayConfigView(BaseConfigView):

    def _get(self, request, display_id, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _context['display'] = models.Display.objects.get(id=display_id)
        return _context



