from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.core.files import File
from django.core.exceptions import ValidationError

from framarama.base.views import BaseView
from framarama.base import frontend
from frontend import views
from frontend import forms
from frontend import models
from config.models import Frame

class BaseSetupView(BaseView):

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _frontend = frontend.Frontend.get()
        _config = _frontend.get_config()
        _context['frontend'] = _frontend
        _context['config'] = _config.get_config() if _frontend.is_configured() else None
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend = frontend.Frontend.get()
        _config = _frontend.get_config()
        _context['frontend'] = _frontend
        _context['config'] = _config.get_config() if _frontend.is_configured() else None
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
            frontend.Singleton.clear()
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
            frontend.Singleton.clear()
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
            if frontend.Frontend.get().is_initialized():
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
            if frontend.Frontend.get().db_access():
                return {
                    'status': 'success',
                    'message': 'Database access successful'
                }
            else:
                return {
                    'status': 'error',
                    'message': 'No database access possible'
                }
        except Exception as e:
            return {
               'status': 'error',
               'message': 'Error accessing database: ' + str(e)
            }
 

class DisplayStatusView(BaseStatusView):

    def _status(self, context):
        try:
            if frontend.Frontend.get().api_access():
                _display = frontend.Frontend.get().get_display()
                return {
                    'status': 'success',
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
            else:
                return {
                    'status': 'error',
                    'message': 'No display configured',
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': 'Error accessing API: ' + str(e)
            }
 

class BaseFrontendView(BaseSetupView):

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _frontend = _context['frontend']
        if not _frontend.is_initialized():
            return {'_response': HttpResponseRedirect(reverse('fe_index'))}
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend = _context['frontend']
        if not _frontend.is_initialized():
            return {'_response': HttpResponseRedirect(reverse('fe_index'))}
        return _context


class OverviewDashboardView(BaseFrontendView):
    template_name = 'frontend/dashboard.overview.html'


class DisplayDashboardView(BaseFrontendView):
    template_name = 'frontend/dashboard.display.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        return _context

class ImageDisplayDashboardView(BaseFrontendView):

    def _get(self, request, nr, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _files = list(_frontend_device.get_files().values())
        _file = _files[nr] if nr >= 0 and nr < len(_files) else _files[0]
        return {'_response': HttpResponse(_file['image'], _file['json']['mime'])}


class DeviceDashboardView(BaseFrontendView):
    template_name = 'frontend/dashboard.device.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _mem_total = _frontend_device.run_capability(frontend.FrontendCapability.MEM_TOTAL)
        _mem_free = _frontend_device.run_capability(frontend.FrontendCapability.MEM_FREE)
        _context['mem'] = {
          'total': _mem_total,
          'free': _mem_free,
          'usage': int((_mem_total - _mem_free) / _mem_total * 100)
        }
        _uptime = _frontend_device.run_capability(frontend.FrontendCapability.SYS_UPTIME)
        _context['sys'] = {
          'uptime' : {
            'total': _uptime,
            'seconds': int(_uptime % 60),
            'minutes': int(_uptime % 3600 / 60),
            'hours': int(_uptime % 86400 / 3600),
            'days': int(_uptime / 86400),
          }
        }
        _context['cpu'] = {
          'load': _frontend_device.run_capability(frontend.FrontendCapability.CPU_LOAD),
          'temp': _frontend_device.run_capability(frontend.FrontendCapability.CPU_TEMP),
        }
        _context['network'] = {
          'config': _frontend_device.run_capability(frontend.FrontendCapability.NET_CONFIG),
        }
        return _context

