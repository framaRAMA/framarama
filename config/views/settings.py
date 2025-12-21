
from django.conf import settings
from django.forms import formset_factory
from django.views.generic import RedirectView
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError

from framarama.base import forms as bforms
from config import models as models
from config.views import base
from config.forms import settings as forms


class ListSettingsView(base.BaseConfigView):
    template_name = 'config/settings.list.html'


class ListVarsSettingsView(base.BaseConfigView):
    template_name = 'config/settings.vars.list.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _page = request.GET.get('page')
        _page_size = request.GET.get('page_size', 20)
        _result = {}
        _result['variables'] = Paginator(self.qs().settings_vars, _page_size).get_page(_page)
        _context.update(_result)
        return _context


class CreateVarsSettingsView(base.BaseConfigView):
    template_name = 'config/settings.vars.create.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _context['form'] = forms.VariablesSettingsForm()
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _settings = models.Settings(user=request.user, category=models.Settings.CAT_VARIABLE)
        _form = forms.VariablesSettingsForm(request.POST, instance=_settings)
        if _form.is_valid():
            _form.save()
            self.redirect(_context, 'settings_vars_list')
        _context['form'] = _form
        return _context


class UpdateVarsSettingsView(base.BaseConfigView):
    template_name = 'config/settings.vars.edit.html'

    def _get(self, request, settings_id, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _settings = self.qs().settings_vars.get(pk=settings_id)
        _context['form'] = forms.VariablesSettingsForm(instance=_settings)
        return _context

    def _post(self, request, settings_id, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _settings = self.qs().settings_vars.get(pk=settings_id)
        _form = forms.VariablesSettingsForm(request.POST, instance=_settings)
        if _form.is_valid():
            _settings = _form.save()
            self.redirect(_context, 'settings_vars_list')
        _context['form'] = _form
        return _context


class ActionVarsSettingsView(base.BaseConfigView):

    def _get(self, request, settings_id, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _settings = self.qs().settings_vars.get(pk=settings_id)
        _action = request.GET['action']
        if _action == 'delete':
            _settings.delete()
        self.redirect(_context, 'settings_vars_list')
        return _context

