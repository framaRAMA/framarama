
from django.contrib.auth import views as auth_views

from framarama.base import frontend
from config.views import base
from config.forms import AuthenticationForm, UpdateProfileForm

class LoginView(auth_views.LoginView):
    template_name = "config/login.html"
    authentication_form = AuthenticationForm


class IndexView(base.BaseConfigView):
    template_name = "config/index.html"

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _dashboards = []
        if self._config.is_local_mode():
            _dashboards.append('display_info')
            _dashboards.append('system_info')
            _dashboards.append('software_info')
            _dashboards.append('system_stats')
            _dashboards.append('display_pictures')
        else:
            _dashboards.append('frames_chart')
            _dashboards.append('displays_chart')
            _dashboards.append('software_info')
            _dashboards.append('system_info')
        _context['system'] = frontend.Frontend.get().get_status()
        _context['dashboards'] = _dashboards
        return _context


class ProfileView(base.BaseConfigView):
    template_name = "config/profile_info.html"


class ProfileEditView(base.BaseConfigView):
    template_name = "config/profile_edit.html"

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _context['form'] = UpdateProfileForm(instance=self.request.user)
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _form = UpdateProfileForm(request.POST, instance=self.request.user)
        if _form.is_valid():
            _form.save()
            self.redirect(_context, 'profile_info')
        _context['form'] = _form
        return _context


class LogoutView(auth_views.LogoutView):
    pass


