from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.core.files import File
from django.core.exceptions import ValidationError

from framarama.base import frontend
from frontend import forms
from frontend.views import base


class StartupView(base.BaseSetupView):
    template_name = 'frontend/startup.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _context['return'] = request.GET['return'] if 'return' in request.GET else ''
        return _context


class SetupView(base.BaseFrontendView):
    template_name = 'frontend/setup.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _frontend = _context['frontend']
        if _frontend.is_setup() and 'edit' not in request.GET:
            _context['_response'] = HttpResponseRedirect(reverse('fe_dashboard'))
        return _context


class LocalModeSetupView(base.BaseSetupView):
    template_name = 'frontend/setup.mode.local.html'

    def _update_config(self, config):
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
        eval(_db, {}, {})
        _file = File(open(settings.BASE_DIR / 'framarama' / 'settings_db.py', 'w'))
        _file.write('dbs = ' + _db)
        _file.close()

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _config = _context['config']
        _context['form'] = forms.LocalModeSetupForm(initial={'mode':'local'}, instance=_config)
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _config = _context['config']
        _form = forms.LocalModeSetupForm(request.POST, instance=_config)
        if _form.is_valid():
            _config = _form.save()
            frontend.Singleton.clear()
            if _config.mode == 'local' and _config.local_db_type == 'mysql':
                try:
                    self._update_config(vars(_config))
                    _context['_response'] = HttpResponseRedirect(reverse('fe_dashboard'))
                except Exception as e:
                    _form.add_error('__all__', ValidationError('Error saving settings (' + str(e) +')'))
            else:
                _context['_response'] = HttpResponseRedirect(reverse('fe_dashboard'))
        _context['form'] = _form
        return _context


class CloudModeSetupView(base.BaseSetupView):
    template_name = 'frontend/setup.mode.cloud.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _config = _context['config']
        _context['form'] = forms.CloudModeSetupForm(initial={'mode':'cloud'}, instance=_config)
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _config = _context['config']
        _form = forms.CloudModeSetupForm(request.POST, instance=_config)
        if _form.is_valid():
            _form.save()
            frontend.Singleton.clear()
            _context['_response'] = HttpResponseRedirect(reverse('fe_dashboard'))
        _context['form'] = _form
        return _context


class DisplaySetupView(base.BaseSetupView):
    template_name = 'frontend/setup.display.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _config = _context['config']
        _context['form'] = forms.DisplaySetupForm(instance=_config)
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _config = _context['config']
        _form = forms.DisplaySetupForm(request.POST, instance=_config)
        if _form.is_valid():
            _form.save()
            frontend.Singleton.clear()
            _context['_response'] = HttpResponseRedirect(reverse('fe_dashboard'))
        _context['form'] = _form
        return _context

