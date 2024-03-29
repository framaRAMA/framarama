from django.conf import settings
from django.apps import apps
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode

from framarama.base import frontend
from framarama.base.views import BaseView
from framarama.base.utils import Filesystem


class BaseSetupView(BaseView):
    PAGE_FE_STARTUP = 'fe_startup'

    def _tz(self, context):
        if context['config'] and context['config'].sys_time_zone:
            return context['config'].sys_time_zone
        return super()._tz(context)

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

    def _update_config(self, config):
        if config:
            _vars = config
            _db = (
                "{\n"
                "  'config': {\n"
                "    'NAME': '%(local_db_name)s',\n"
                "    'ENGINE': 'django.db.backends.mysql',\n"
                "    'USER': '%(local_db_user)s',\n"
                "    'PASSWORD': '%(local_db_pass)s',\n"
                "    'HOST': '%(local_db_host)s',\n"
                "  }\n"
                "}\n"
            ) % _vars
        else:
            _db = "{}\n"
        eval(_db, {}, {})
        Filesystem.file_write(settings.BASE_DIR / 'framarama' / 'settings_db.py', b'dbs = ' + _db.encode())

    def redirect_startup(self, context, page=None, url=None, message=None, wait=None, negate=False, errors=True):
        if page is None and url is None:
            page = self.view_name(self.request)
        _query = 'startup=1'
        _query = _query + ('&' + urlencode({'return': reverse(page)}) if page else '')
        _query = _query + ('&' + urlencode({'return': url}) if url else '')
        _query = _query + ('&' + urlencode({'message': message}) if message else '')
        _query = _query + ('&' + urlencode({'wait': wait}) if wait else '')
        _query = _query + ('&' + urlencode({'negate': '1'}) if negate else '')
        _query = _query + ('&' + urlencode({'errors': '0'}) if not errors else '')
        self.redirect(context, BaseSetupView.PAGE_FE_STARTUP, _query)


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

