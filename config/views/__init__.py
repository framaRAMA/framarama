
from django.contrib.auth import views as auth_views

from config.views import base
from config.forms import AuthenticationForm

class LoginView(auth_views.LoginView):
    template_name = "config/login.html"
    authentication_form = AuthenticationForm


class IndexView(base.BaseConfigView):
    template_name = "config/index.html"


class LogoutView(auth_views.LogoutView):
    pass


