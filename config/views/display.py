
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

from config import models
from config.views import base
from config.forms import display as forms

class ListDisplayView(base.BaseConfigView):
    template_name = "config/display.list.html"


class CreateDisplayView(base.BaseConfigView):
    template_name = 'config/display.create.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _context['form'] = forms.CreateDisplayForm()
        return _context

    def _post(self, request, *args, **kwargs):
        _form = forms.CreateDisplayForm(request.POST)
        if _form.is_valid():
            _display = models.Display(user=request.user, name=_form.cleaned_data['name'], description=_form.cleaned_data['description'], enabled=_form.cleaned_data['enabled'])
            _display.save()
            return {'_response': HttpResponseRedirect(reverse('display_info', args=[_display.id]))}
        _context = super()._get(request, *args, **kwargs)
        _context['form'] = _form
        return _context


class ViewInfoDisplayView(base.BaseDisplayConfigView):
    template_name= 'config/display.info.html'


class UpdateDisplayView(base.BaseDisplayConfigView):
    template_name = 'config/display.edit.html'

    def _get(self, request, display_id, *args, **kwargs):
        _context = super()._get(request, display_id, *args, **kwargs)
        _display = _context['display']
        _context['form'] = forms.UpdateDisplayForm(instance=_display, user=request.user)
        return _context

    def _post(self, request, display_id, *args, **kwargs):
        _context = super()._get(request, display_id, *args, **kwargs)
        _display = _context['display']
        _form = forms.UpdateDisplayForm(request.POST, instance=_display, user=request.user)
        if _form.is_valid():
            _form.save()
            return {'_response': HttpResponseRedirect(reverse('display_info', args=[_display.id]))}
        _context['form'] = _form
        return _context


class ViewDeviceDisplayView(base.BaseDisplayConfigView):
    template_name= 'config/display.device.html'


class UpdateDeviceDisplayView(base.BaseDisplayConfigView):
    template_name = 'config/display.device.edit.html'

    def _get(self, request, display_id, *args, **kwargs):
        _context = super()._get(request, display_id, *args, **kwargs)
        _display = _context['display']
        _context['form'] = forms.UpdateDeviceDisplayForm(instance=_display)
        return _context

    def _post(self, request, display_id, *args, **kwargs):
        _context = super()._get(request, display_id, *args, **kwargs)
        _display = _context['display']
        _form = forms.UpdateDeviceDisplayForm(request.POST, instance=_display)
        if _form.is_valid():
            _form.save()
            return {'_response': HttpResponseRedirect(reverse('display_device', args=[_display.id]))}
        _context['form'] = _form
        return _context


class ViewTimeDisplayView(base.BaseDisplayConfigView):
    template_name= 'config/display.time.html'


class UpdateTimeDisplayView(base.BaseDisplayConfigView):
    template_name = 'config/display.time.edit.html'

    def _get(self, request, display_id, *args, **kwargs):
        _context = super()._get(request, display_id, *args, **kwargs)
        _display = _context['display']
        _context['form'] = forms.UpdateTimeDisplayForm(instance=_display)
        return _context

    def _post(self, request, display_id, *args, **kwargs):
        _context = super()._get(request, display_id, *args, **kwargs)
        _display = _context['display']
        _form = forms.UpdateTimeDisplayForm(request.POST, instance=_display)
        if _form.is_valid():
            _form.save()
            return {'_response': HttpResponseRedirect(reverse('display_time', args=[_display.id]))}
        _context['form'] = _form
        return _context


class ViewAccessDisplayView(base.BaseDisplayConfigView):
    template_name= 'config/display.access.html'


class UpdateAccessDisplayView(base.BaseDisplayConfigView):
    template_name = 'config/display.access.edit.html'

    def _get(self, request, display_id, *args, **kwargs):
        _context = super()._get(request, display_id, *args, **kwargs)
        _display = _context['display']
        _context['form'] = forms.UpdateAccessDisplayForm(instance=_display)
        return _context

    def _post(self, request, display_id, *args, **kwargs):
        _context = super()._get(request, display_id, *args, **kwargs)
        _display = _context['display']
        _form = forms.UpdateAccessDisplayForm(request.POST, instance=_display)
        if _form.is_valid():
            _form.save()
            return {'_response': HttpResponseRedirect(reverse('display_access', args=[_display.id]))}
        _context['form'] = _form
        return _context



