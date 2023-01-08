from django.apps import apps
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode

from framarama.base import frontend
from framarama.base.views import BaseView


class BaseSetupView(BaseView):
    PAGE_FE_STARTUP = 'fe_startup'

    def _process_base_setup_view(self, request, context, *args, **kwargs):
        _frontend = frontend.Frontend.get()
        context['now'] = timezone.now()
        context['frontend'] = _frontend
        context['config'] = _frontend.get_config().get_config() if _frontend.is_configured() else None
        if not _frontend.is_initialized() and self.view_name(request) != BaseSetupView.PAGE_FE_STARTUP:
            self.redirect_startup(context, url=self.url(request))
        return context

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        return self._process_base_setup_view(request, _context, *args, **kwargs)

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        return self._process_base_setup_view(request, _context, *args, **kwargs)

    def redirect_startup(self, context, page=None, url=None, message=None):
        if page is None and url is None:
            page = self.view_name(self.request)
        _query = 'startup=1'
        _query = _query + '&' + urlencode({'return': reverse(page)}) if page else ''
        _query = _query + '&' + urlencode({'return': url}) if url else ''
        _query = _query + '&' + urlencode({'message': message}) if message else ''
        self.redirect(context, BaseSetupView.PAGE_FE_STARTUP, _query)


class BaseStatusView(BaseSetupView):

    def _get(self, request, *args, **kwargs):
       _context = super()._get(request, *args, **kwargs)
       _context['_response'] = JsonResponse(self._status(_context))
       return _context

 
class BaseFrontendView(BaseSetupView):
    PAGE_FE_INDEX = 'fe_index'

    def _process_base_frontend_view(self, request, context, *args, **kwargs):
        _frontend = context['frontend']
        if not _frontend.is_setup() and self.view_name(request) != BaseFrontendView.PAGE_FE_INDEX:
            self.redirect(context, BaseFrontendView.PAGE_FE_INDEX)
        return context

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        return self._process_base_frontend_view(request, _context, *args, **kwargs)

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        return self._process_base_frontend_view(request, _context, *args, **kwargs)

    def get_scheduler(self):
        return apps.get_app_config('frontend').get_scheduler()

