from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.core.files import File
from django.core.exceptions import ValidationError

from framarama.base.views import BaseView
from framarama.base import utils
from frontend import views
from frontend import forms
from frontend import models
from config.models import Frame


class BaseSetupView(BaseView):

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _context['config'] = utils.Frontend.get().get_config().get_config()
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _context['config'] = utils.Frontend.get().get_config().get_config()
        return _context


class SetupView(BaseSetupView):
    template_name = 'frontend/setup.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        if _context['config'] and 'edit' not in request.GET:
            return {'_response': HttpResponseRedirect(reverse('fe_dashboard'))}
        return _context


class LocalSetupView(BaseSetupView):
    template_name = 'frontend/setup.local.html'

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
        _context['form'] = forms.LocalSetupForm(initial={'mode':'local'}, instance=_config)
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _config = _context['config']
        _form = forms.LocalSetupForm(request.POST, instance=_config)
        if _form.is_valid():
            _config = _form.save()
            utils.Singleton.clear()
            if _config.mode == 'local' and _config.local_db_type == 'mysql':
                try:
                    self._update_config(vars(_config))
                    return {'_response': HttpResponseRedirect(reverse('fe_dashboard'))}
                except Exception as e:
                    _form.add_error('__all__', ValidationError('Error saving settings (' + str(e) +')'))
            else:
                return {'_response': HttpResponseRedirect(reverse('fe_dashboard'))}
        _context['form'] = _form
        return _context


class CloudSetupView(BaseSetupView):
    template_name = 'frontend/setup.cloud.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _config = _context['config']
        _context['form'] = forms.CloudSetupForm(initial={'mode':'cloud'}, instance=_config)
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _config = _context['config']
        _form = forms.CloudSetupForm(request.POST, instance=_config)
        if _form.is_valid():
            _form.save()
            utils.Singleton.clear()
            return {'_response': HttpResponseRedirect(reverse('fe_dashboard'))}
        _context['form'] = _form
        return _context


class BaseStatusView(BaseSetupView):

    def _get(self, request, *args, **kwargs):
       _context = super()._get(request, *args, **kwargs)
       return {'_response': JsonResponse(self._status(_context))}
 

class SetupStatusView(BaseStatusView):

    def _status(self, context):
        try:
            if utils.Frontend.get().is_initialized():
                return {
                    'status': 'success',
                    'message': 'Configuration setup completed'
                }
            return {
                'status': 'testing',
                'message': 'Configuration setup not available'
            }
        except Exception as e:
            return {
               'status': 'error',
               'message': 'Error checking setup status: ' + str(e)
            }
 

class DatabaseStatusView(BaseStatusView):

    def _status(self, context):
        try:
            _frame = Frame.objects.all().first()
            return {
                'status': 'success',
                'message': 'Database access successful'
            }
        except Exception as e:
            return {
               'status': 'error',
               'message': 'Error accessing database: ' + str(e)
            }
 

class DisplayStatusView(BaseStatusView):

    def _status(self, context):
        try:
            _display = utils.Frontend.get(force=True).get_display()
            return {
                'status': True,
                'message': 'Successful API access',
                'data': {
                  'display': {
                    'id': _display.get_id(),
                    'name': _display.get_name(),
                    'enabled': _display.get_enabled(),
                    'device_type': _display.get_device_type(),
                    'device_type_name': _display.get_device_type_name(),
                    'device_width': _display.get_device_width(),
                    'device_height': _display.get_device_height()
                  }
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': 'Error accessing API: ' + str(e)
            }
 

class BaseFrontendView(BaseSetupView):

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _config = _context['config']
        if _config is None:
            return {'_response': HttpResponseRedirect(reverse('fe_index'))}
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        if _context['config'] is None:
            return {'_response': HttpResponseRedirect(reverse('fe_index'))}
        return _context


class OverviewDashboardView(BaseFrontendView):
    template_name = 'frontend/dashboard.overview.html'


class DeviceDashboardView(BaseFrontendView):
    template_name = 'frontend/dashboard.device.html'


