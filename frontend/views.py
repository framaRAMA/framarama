from django.apps import apps
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.core.files import File
from django.core.exceptions import ValidationError
from django.utils import timezone

from framarama.base.views import BaseView
from framarama.base import frontend
from frontend import views
from frontend import forms
from frontend import models
from frontend import jobs
from config.models import Frame

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


class SetupView(BaseSetupView):
    template_name = 'frontend/setup.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        if _context['config'] and 'edit' not in request.GET:
            _context['_response'] = HttpResponseRedirect(reverse('fe_dashboard'))
        return _context


class LocalModeSetupView(BaseSetupView):
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


class CloudModeSetupView(BaseSetupView):
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


class DisplaySetupView(BaseSetupView):
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


class BaseStatusView(BaseSetupView):

    def _get(self, request, *args, **kwargs):
       _context = super()._get(request, *args, **kwargs)
       _context['_response'] = JsonResponse(self._status(_context))
       return _context
 

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
            _context['_response'] = HttpResponseRedirect(reverse('fe_index'))
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend = _context['frontend']
        if not _frontend.is_initialized():
            _context['_response'] = HttpResponseRedirect(reverse('fe_index'))
        return _context


class OverviewDashboardView(BaseFrontendView):
    template_name = 'frontend/dashboard.overview.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _context['app'] = {
            'revision': _frontend_device.run_capability(frontend.FrontendCapability.APP_REVISION),
        }
        return _context


class DisplayDashboardView(BaseFrontendView):
    template_name = 'frontend/dashboard.display.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _scheduler = apps.get_app_config('frontend').get_scheduler()
        _context['files'] = _frontend_device.get_files().items()
        _action = self.request.GET.get('action')
        if _action == 'display.toggle':
          if _frontend_device.run_capability(frontend.FrontendCapability.DISPLAY_STATUS):
              _frontend_device.run_capability(frontend.FrontendCapability.DISPLAY_OFF)
          else:
              _frontend_device.run_capability(frontend.FrontendCapability.DISPLAY_ON)
        elif _action == 'display.refresh':
            _scheduler.trigger(jobs.Jobs.FE_NEXT_ITEM, force=True)
        _context['display'] = {
            'status': _frontend_device.run_capability(frontend.FrontendCapability.DISPLAY_STATUS),
            'size': _frontend_device.run_capability(frontend.FrontendCapability.DISPLAY_SIZE),
            'refresh': _scheduler.running(jobs.Jobs.FE_NEXT_ITEM, True),
        }
        return _context

class ImageDisplayDashboardView(BaseFrontendView):

    def _get(self, request, nr, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _files = list(_frontend_device.get_files().values())
        _file = _files[nr] if nr >= 0 and nr < len(_files) else _files[0]
        if self.request.GET.get('type') == 'preview':
            _context['_response'] = HttpResponse(_file['preview'], _file['json']['mime'])
        else:
            _context['_response'] = HttpResponse(_file['image'], _file['json']['mime'])
        return _context


class DeviceDashboardView(BaseFrontendView):
    template_name = 'frontend/dashboard.device.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _action = self.request.GET.get('action')
        if _action == 'wifi.save':
            _name = self.request.GET.get('name')
            _pass = self.request.GET.get('password')
            _frontend_device.run_capability(frontend.FrontendCapability.NET_PROFILE_SAVE, name=_name, password=_pass)
            _context['_response'] = HttpResponseRedirect(reverse('fe_dashboard_device') + '?action=wifi.list')
            return _context
        elif _action == 'wifi.delete':
            _name = self.request.GET.get('name')
            _frontend_device.run_capability(frontend.FrontendCapability.NET_PROFILE_DELETE, name=_name)
            _context['_response'] = HttpResponseRedirect(reverse('fe_dashboard_device') + '?action=wifi.list')
            return _context
        elif _action == 'wifi.connect':
            _name = self.request.GET.get('name')
            _frontend_device.network_connect(_name)
            _context['_response'] = HttpResponseRedirect(reverse('fe_dashboard_device') + '?action=wifi.list')
            return _context
        _wifi = None
        if _action == 'device.log':
            _lines = _frontend_device.run_capability(frontend.FrontendCapability.APP_LOG)
            _context['log'] = _lines
        elif _action == 'device.restart':
            _frontend_device.run_capability(frontend.FrontendCapability.APP_RESTART)
        elif _action == 'device.shutdown':
            _frontend_device.run_capability(frontend.FrontendCapability.APP_SHUTDOWN)
        elif _action == 'wifi.list':
            _profiles = _frontend_device.run_capability(frontend.FrontendCapability.NET_PROFILE_LIST)
            _ap_active = frontend.FrontendCapability.nmcli_ap_active(_profiles)
            if _ap_active:
                _networks = _frontend_device.network_status()['networks']
            else:
                _networks = _frontend_device.run_capability(frontend.FrontendCapability.NET_WIFI_LIST)
            if 'framarama' in _profiles:
                del _profiles['framarama']
            _networks.update({_name: {'ssid': _name, 'active': False} for _name in _profiles if _name not in _networks})
            _networks = [_networks[_name] | {'profile':_name if _name in _profiles else ''} for _name in _networks]
            _wifi = {
              'networks': _networks,
              'profiles': _profiles,
              'ap': _ap_active
            }
        elif _action == 'wifi.ap':
            _frontend_device.network_ap_toggle()
            _context['_response'] = HttpResponseRedirect(reverse('fe_dashboard_device') + '?action=wifi.list')
            return _context
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
        _context['disk'] = {
          'datafree': _frontend_device.run_capability(frontend.FrontendCapability.DISK_DATA_FREE),
          'tmpfree': _frontend_device.run_capability(frontend.FrontendCapability.DISK_TMP_FREE),
        }
        _context['cpu'] = {
          'load': _frontend_device.run_capability(frontend.FrontendCapability.CPU_LOAD),
          'temp': _frontend_device.run_capability(frontend.FrontendCapability.CPU_TEMP),
        }
        _context['network'] = {
          'config': _frontend_device.run_capability(frontend.FrontendCapability.NET_CONFIG),
          'wifi': _wifi
        }
        return _context


class HelpSystemView(BaseFrontendView):
    template_name = 'frontend/system.help.html'


class UsbSystemView(BaseFrontendView):
    template_name = 'frontend/system.usb.html'


class LabelSystemView(BaseFrontendView):
    template_name = 'frontend/system.label.html'


