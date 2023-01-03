from django.apps import apps
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils import timezone

from framarama.base import frontend
from framarama.base.views import BaseView


class BaseSetupView(BaseView):

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _frontend = frontend.Frontend.get()
        _config = _frontend.get_config()
        _context['now'] = timezone.now()
        _context['frontend'] = _frontend
        _context['config'] = _config.get_config() if _frontend.is_configured() else None
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend = frontend.Frontend.get()
        _config = _frontend.get_config()
        _context['now'] = timezone.now()
        _context['frontend'] = _frontend
        _context['config'] = _config.get_config() if _frontend.is_configured() else None
        return _context


class BaseStatusView(BaseSetupView):

    def _get(self, request, *args, **kwargs):
       _context = super()._get(request, *args, **kwargs)
       _context['_response'] = JsonResponse(self._status(_context))
       return _context

 
class BaseFrontendView(BaseSetupView):

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _frontend = _context['frontend']
        if not _frontend.is_initialized():
            _context['_response'] = HttpResponseRedirect(reverse('fe_index'))
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend = _context['frontend']
        if not _frontend.is_initialized():
            _context['_response'] = HttpResponseRedirect(reverse('fe_index'))
        return _context

    def get_scheduler(self):
        return apps.get_app_config('frontend').get_scheduler()




