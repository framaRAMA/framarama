from django.core.exceptions import ValidationError

from framarama.base import frontend
from frontend import forms
from frontend.views import base


class StartupView(base.BaseSetupView):
    template_name = 'frontend/startup.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        if request.GET.get('message', None):
            _context['message'] = request.GET['message']
        if request.GET.get('return', None):
            _context['return'] = request.GET['return']
        if request.GET.get('wait', None):
            _context['wait'] = int(request.GET['wait'])*1000
        if request.GET.get('negate', None):
            _context['negate'] = int(request.GET['negate'])
        if request.GET.get('errors', None):
            _context['errors'] = int(request.GET['errors'])
        return _context


class SetupView(base.BaseFrontendView):
    template_name = 'frontend/setup.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _frontend = _context['frontend']
        if _frontend.is_setup() and 'edit' not in request.GET:
            self.redirect(_context, 'fe_dashboard')
        return _context


class LocalModeSetupView(base.BaseSetupView):
    template_name = 'frontend/setup.mode.local.html'

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
                    self.redirect_startup(_context, 'fe_dashboard', message='config.save')
                except Exception as e:
                    _form.add_error('__all__', ValidationError('Error saving settings (' + str(e) +')'))
            else:
                self._update_config(None)
                self.redirect(_context, 'fe_dashboard')
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
            self._update_config(None)
            self.redirect_startup(_context, 'fe_dashboard', message='config.save')
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
            self.redirect_startup(_context, 'fe_dashboard', message='config.save')
        _context['form'] = _form
        return _context

class SoftwareSetupView(base.BaseSetupView):
    template_name = 'frontend/setup.software.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _config = _context['config']
        _context['form'] = forms.SoftwareSetupForm(instance=_config)
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _config = _context['config']
        _form = forms.SoftwareSetupForm(request.POST, instance=_config)
        if _form.is_valid():
            _form.save()
            frontend.Singleton.clear()
            self.redirect_startup(_context, 'fe_dashboard_software', message='config.save')
        _context['form'] = _form
        return _context

