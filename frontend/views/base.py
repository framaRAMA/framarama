from django.apps import apps
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode

from framarama.base import frontend
from framarama.base.views import BaseView


class BaseSetupView(BaseView):
    PAGE_FE_STARTUP = 'fe_startup'

    def _process(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _frontend = frontend.Frontend.get()
        _config = _frontend.get_config()
        _context['now'] = timezone.now()
        _context['frontend'] = _frontend
        _context['config'] = _config.get_config() if _frontend.is_configured() else None
        if not _frontend.is_initialized() and self.view_name(request) != BaseSetupView.PAGE_FE_STARTUP:
            self.redirect_startup(_context, url=self.url(request))
        return _context

    def _get(self, request, *args, **kwargs):
        return self._process(request, *args, **kwargs)

    def _post(self, request, *args, **kwargs):
        return self._process(request, *args, **kwargs)

    def redirect_startup(self, context, page=None, url=None):
        _query = 'startup=1'
        _query = _query + '&' + urlencode({'return': reverse(page)}) if page else ''
        _query = _query + '&' + urlencode({'return': url}) if url else ''
        self.redirect(context, BaseSetupView.PAGE_FE_STARTUP, _query)


class BaseStatusView(BaseSetupView):

    def _get(self, request, *args, **kwargs):
       _context = super()._get(request, *args, **kwargs)
       _context['_response'] = JsonResponse(self._status(_context))
       return _context

 
class BaseFrontendView(BaseSetupView):

    def get_scheduler(self):
        return apps.get_app_config('frontend').get_scheduler()

