
from framarama.base import frontend, device, utils
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
        _capability = _frontend_device.get_capability()
        _scheduler = self.get_scheduler()
        _context['items'] = _frontend_device.get_items()
        _context['streamed'] = _frontend_device.get_streamed()
        _action = self.request.GET.get('action')
        if _action == 'display.toggle':
          _frontend_device.display_toggle(force=True)
        elif _action == 'display.refresh':
            _scheduler.trigger_job(jobs.Scheduler.FE_NEXT_ITEM, force=True)
        elif _action == 'display.set':
            _scheduler.run_job(jobs.Scheduler.FE_ACTIVATE_ITEM, lambda: _frontend_device.activate(int(self.request.GET['item'])))
        elif _action == 'display.stream':
            _scheduler.stream_toggle()
        if _action:
            self.redirect(_context)
        _context['display'] = {
            'status': _capability.display_status(),
            'size': _capability.display_size(),
            'refresh': _scheduler.running_jobs(jobs.Scheduler.FE_NEXT_ITEM, starts_with=True),
            'set': _scheduler.running_jobs(jobs.Scheduler.FE_ACTIVATE_ITEM),
            'stream': _scheduler.is_streaming()
        }
        return _context


class ImageDisplayDashboardView(base.BaseFrontendView):

    def _get(self, request, nr, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _items = _frontend_device.get_items()
        _item = _items[nr] if nr >= 0 and nr < len(_items) else _items[0]
        if self.request.GET.get('type') == 'preview':
            self.response(_context, _item.preview(), _item.preview_mime())
        else:
            self.response(_context, _item.data(), _item.mime())
        return _context


class StreamDisplayDashboardView(base.BaseFrontendView):

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _name = request.POST.get('name', None)
        _final = request.POST.get('final', 0)
        _ts = request.POST.get('ts', 0)
        _data = request.FILES.get('data', None)

        _frontend = _context['frontend']
        _device = _frontend.get_device()
        try:
            _status = _device.upload_streamed(_data, _ts, _final)
            if str(_final) == "1":
                _display = _frontend.get_display()
                self.get_scheduler().run_job(jobs.Scheduler.FE_ACTIVATE_ITEM, lambda: self._finish_streamed(_device, _display))
                self.response_json(_context, {'status': 'OK', 'message': 'Start finalizing', 'ts': _status['ts']})
            else:
                self.response_json(_context, {'status': 'OK', 'message': 'Chunk added', 'ts': _status['ts']})
        except Exception as e:
            self.response_json(_context, {'status': 'ERROR', 'message': str(e)})
        return _context

    def _finish_streamed(self, device, display):
        device.finish_file(display, device.upload_file())
        device.activate_item(device.get_streamed()[0])

class ItemStreamDisplayDashboardView(base.BaseFrontendView):

    def _item(self, context, nr):
        _frontend_device = context['frontend'].get_device()
        _items = _frontend_device.get_streamed()
        if nr >= 0 and nr < len(_items):
            return _items[nr]
        elif len(_items) > 0:
            return _items[0]

    def _get(self, request, nr, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _item = self._item(_context, nr)
        _modified_since = request.headers.get('if-modified-since', None)
        if not _item:
            self.response_image_default(_context)
        elif _modified_since and utils.DateTime.before(_item.time(), utils.DateTime.parse(_modified_since)):
            self.response(_context, status=304, headers={
              'Last-Modified': _item.time().strftime("%a, %d %b %Y %H:%M:%S GMT")
            })
        elif self.request.GET.get('type') == 'preview':
            self.response(_context, _item.preview(), _item.preview_mime())
        else:
            self.response(_context, _item.data(), _item.mime())
        return _context


class DeviceDashboardView(base.BaseFrontendView):
    template_name = 'frontend/dashboard.device.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _capability = _frontend_device.get_capability()
        _scheduler = self.get_scheduler()
        _action = self.request.GET.get('action')
        if _action == 'wifi.save':
            _name = self.request.GET.get('name')
            _pass = self.request.GET.get('password')
            _capability.net_profile_save(name=_name, password=_pass)
            self.redirect(_context, query='action=wifi.list')
            return _context
        elif _action == 'wifi.delete':
            _name = self.request.GET.get('name')
            _capability.net_profile_delete(name=_name)
            self.redirect(_context, query='action=wifi.list')
            return _context
        elif _action == 'wifi.connect':
            _name = self.request.GET.get('name')
            _scheduler.run_job(jobs.Scheduler.FE_WIFI_CONNECT, lambda: _frontend_device.network_connect(_name), delay=2)
            self.redirect_startup(_context, message='wifi.connect', negate=True)
            return _context
        _wifi = None
        if _action == 'device.log':
            _lines = _capability.app_log()
            _context['log'] = _lines
        elif _action == 'device.restart':
            _scheduler.run_job(jobs.Scheduler.FE_DEVICE_RESTART, lambda: _capability.app_restart(), delay=2)
            self.redirect_startup(_context, message='device.restart', wait=3, errors=False)
        elif _action == 'device.shutdown':
            _scheduler.run_job(jobs.Scheduler.FE_DEVICE_SHUTDOWN, lambda: _capability.app_shutdown(), delay=2)
            self.redirect_startup(_context, message='device.shutdown', negate=True)
        elif _action == 'wifi.list':
            _profiles = _capability.net_profile_list()
            _ap_active = _capability.net_ap_active(_profiles)
            if _ap_active:
                _networks = _frontend_device.network_status()['networks']
            else:
                _networks = _capability.net_wifi_list()
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
            _scheduler.run_job(jobs.Scheduler.FE_WIFI_AP, lambda: _frontend_device.network_ap_toggle(), delay=2)
            self.redirect_startup(_context, message='wifi.ap', negate=True)
            return _context
        _mem_total = _capability.mem_total()
        _mem_free = _capability.mem_free()
        _context['mem'] = {
          'total': _mem_total,
          'free': _mem_free,
          'usage': int((_mem_total - _mem_free) / _mem_total * 100)
        }
        _uptime = _capability.sys_uptime()
        _disk_tmp = _capability.disk_tmp_free()
        _disk_data = _capability.disk_data_free()
        _context['sys'] = {
          'uptime' : _uptime
        }
        _context['disk'] = {
          'datafree': _disk_data[1],
          'tmpfree': _disk_tmp[1],
        }
        _context['cpu'] = {
          'load': _capability.cpu_load(),
          'temp': _capability.cpu_temp(),
        }
        _context['network'] = {
          'config': _capability.net_config(),
          'wifi': _wifi
        }
        return _context


class SoftwareDashboardView(base.BaseFrontendView):
    template_name = 'frontend/dashboard.software.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _capability = _frontend_device.get_capability()
        _revision = _capability.app_revision()
        _scheduler = self.get_scheduler()
        _form_check = forms.SoftwareDashboardCheckForm(initial={
            'url': _revision['remote']['url'],
            'username': '',
            'password': '',
        })
        _form_update = forms.SoftwareDashboardUpdateForm()
        _form_update.fields['revision'].widget.choices = [(_rev, _rev) for _rev in _revision['revisions']]
        _config = _context['config']
        _context.update({
            'app': { 'revision': _revision },
            'form_check': _form_check,
            'check': _scheduler.running_jobs(jobs.Scheduler.FE_APP_CHECK, starts_with=True),
            'form_update': _form_update,
            'update': _scheduler.running_jobs(jobs.Scheduler.FE_APP_UPDATE, starts_with=True),
            'app_update_check' : _config.app_update_check,
            'app_update_check_date' : _config.app_update_check_date,
            'app_update_check_status' : _config.app_update_check_status,
            'app_update_install' : _config.app_update_install,
            'app_update_install_hour' : _config.app_update_install_hour,
            'app_update_install_date' : _config.app_update_install_date,
            'app_update_install_status' : _config.app_update_install_status,
        })
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._post(request, *args, **kwargs)
        _frontend_device = _context['frontend'].get_device()
        _capability = _frontend_device.get_capability()
        _revision = _capability.app_revision()
        _scheduler = self.get_scheduler()
        _form_check = forms.SoftwareDashboardCheckForm(request.POST)
        if _form_check.is_valid():
            _scheduler.trigger_job(jobs.Scheduler.FE_APP_CHECK, 
                url=_form_check.cleaned_data['url'],
                username=_form_check.cleaned_data['username'],
                password=_form_check.cleaned_data['password'],
                force=True)
            self.redirect(_context)
        _form_update = forms.SoftwareDashboardUpdateForm(request.POST)
        if _form_update.is_valid():
            _scheduler.trigger_job(jobs.Scheduler.FE_APP_UPDATE,
                revision=_form_update.cleaned_data['revision'],
                force=True)
            self.redirect_startup(_context, 'fe_dashboard_software', message='app.update', wait=10, errors=False)
        _config = _context['config']
        _context.update({
            'app': { 'revision': _revision },
            'form_check': _form_check,
            'check': _scheduler.running_jobs(jobs.Scheduler.FE_APP_CHECK, starts_with=True),
            'form_update': _form_update,
            'update': _scheduler.running_jobs(jobs.Scheduler.FE_APP_UPDATE, starts_with=True),
            'app_update_check' : _config.app_update_check,
            'app_update_check_date' : _config.app_update_check_date,
            'app_update_check_status' : _config.app_update_check_status,
            'app_update_install' : _config.app_update_install,
            'app_update_install_hour' : _config.app_update_install_hour,
            'app_update_install_date' : _config.app_update_install_date,
            'app_update_install_status' : _config.app_update_install_status,
        })
        return _context

