
from framarama.base import frontend
from frontend import forms
from frontend import models
from frontend import jobs
from frontend.views import base


class OverviewDashboardView(base.BaseFrontendView):
    template_name = 'frontend/dashboard.overview.html'


class DisplayDashboardView(base.BaseFrontendView):
    template_name = 'frontend/dashboard.display.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _scheduler = self.get_scheduler()
        _context['files'] = _frontend_device.get_files().items()
        _action = self.request.GET.get('action')
        if _action == 'display.toggle':
          if _frontend_device.run_capability(frontend.FrontendCapability.DISPLAY_STATUS):
              _frontend_device.run_capability(frontend.FrontendCapability.DISPLAY_OFF)
          else:
              _frontend_device.run_capability(frontend.FrontendCapability.DISPLAY_ON)
        elif _action == 'display.refresh':
            _scheduler.trigger(jobs.Jobs.FE_NEXT_ITEM, force=True)
        elif _action == 'display.set':
            _scheduler.add(lambda: _frontend_device.activate(item=self.request.GET['item']), id=jobs.Jobs.FE_ACTIVATE_ITEM)
        if _action:
            self.redirect(_context)
        _context['display'] = {
            'status': _frontend_device.run_capability(frontend.FrontendCapability.DISPLAY_STATUS),
            'size': _frontend_device.run_capability(frontend.FrontendCapability.DISPLAY_SIZE),
            'refresh': _scheduler.running(jobs.Jobs.FE_NEXT_ITEM, True),
            'set': _scheduler.running(jobs.Jobs.FE_ACTIVATE_ITEM),
        }
        return _context


class ImageDisplayDashboardView(base.BaseFrontendView):

    def _get(self, request, nr, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _files = list(_frontend_device.get_files().values())
        _file = _files[nr] if nr >= 0 and nr < len(_files) else _files[0]
        if self.request.GET.get('type') == 'preview':
            self.response(_context, _file['preview'], _file['json']['mime'])
        else:
            self.response(_context, _file['image'], _file['json']['mime'])
        return _context


class DeviceDashboardView(base.BaseFrontendView):
    template_name = 'frontend/dashboard.device.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _action = self.request.GET.get('action')
        if _action == 'wifi.save':
            _name = self.request.GET.get('name')
            _pass = self.request.GET.get('password')
            _frontend_device.run_capability(frontend.FrontendCapability.NET_PROFILE_SAVE, name=_name, password=_pass)
            self.redirect(_context, 'fe_dashboard_device', 'action=wifi.list')
            return _context
        elif _action == 'wifi.delete':
            _name = self.request.GET.get('name')
            _frontend_device.run_capability(frontend.FrontendCapability.NET_PROFILE_DELETE, name=_name)
            self.redirect(_context, 'fe_dashboard_device', 'action=wifi.list')
            return _context
        elif _action == 'wifi.connect':
            _name = self.request.GET.get('name')
            _frontend_device.network_connect(_name)
            self.redirect(_context, 'fe_dashboard_device', 'action=wifi.list')
            return _context
        _wifi = None
        if _action == 'device.log':
            _lines = _frontend_device.run_capability(frontend.FrontendCapability.APP_LOG)
            _context['log'] = _lines
        elif _action == 'device.restart':
            _frontend_device.run_capability(frontend.FrontendCapability.APP_RESTART)
            self.redirect_startup(_context, page='fe_dashboard_device', message='device.restart')
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
            self.redirect(_context, 'fe_dashboard_device', 'action=wifi.list')
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


class SoftwareDashboardView(base.BaseFrontendView):
    template_name = 'frontend/dashboard.software.html'

    REMOTE_NAME = 'origin'

    def _get(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _revisions = _frontend_device.run_capability(frontend.FrontendCapability.APP_REVISION)
        _scheduler = self.get_scheduler()
        _remotes = _revisions['remotes'] if _revisions else {}
        _form_check = forms.SoftwareDashboardCheckForm(initial={
            'url': _remotes[SoftwareDashboardView.REMOTE_NAME],
            'remotes': _remotes,
            'username': '',
            'password': '',
        })
        _form_update = forms.SoftwareDashboardUpdateForm()
        _form_update.fields['revision'].widget.choices = [(_rev, _rev.replace(SoftwareDashboardView.REMOTE_NAME + '/', '')) for _rev in _revisions['revisions']]
        _context.update({
            'app': { 'revision': _revisions },
            'form_check': _form_check,
            'check': _scheduler.running(jobs.Jobs.FE_APP_CHECK),
            'form_update': _form_update,
            'update': _scheduler.running(jobs.Jobs.FE_APP_UPDATE),
        })
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _revisions = _frontend_device.run_capability(frontend.FrontendCapability.APP_REVISION)
        _scheduler = self.get_scheduler()
        _form_check = forms.SoftwareDashboardCheckForm(request.POST)
        if _form_check.is_valid():
            _scheduler.add(lambda: _frontend_device.run_capability(
                frontend.FrontendCapability.APP_CHECK,
                SoftwareDashboardView.REMOTE_NAME,
                url=_form_check.cleaned_data['url'],
                username=_form_check.cleaned_data['username'],
                password=_form_check.cleaned_data['password']), id=jobs.Jobs.FE_APP_CHECK)
            self.redirect(_context, 'fe_dashboard_software')
        _form_update = forms.SoftwareDashboardUpdateForm(request.POST)
        if _form_update.is_valid():
            _scheduler.add(lambda: _frontend_device.run_capability(
                frontend.FrontendCapability.APP_UPDATE,
                revision=_form_update.cleaned_data['revision']), id=jobs.Jobs.FE_APP_UPDATE)
            self.redirect(_context, 'fe_dashboard_software')
        _context.update({
            'app': { 'revision': _revisions },
            'form_check': _form_check,
            'check': _scheduler.running(jobs.Jobs.FE_APP_CHECK),
            'form_update': _form_update,
            'update': _scheduler.running(jobs.Jobs.FE_APP_UPDATE),
        })
        return _context

