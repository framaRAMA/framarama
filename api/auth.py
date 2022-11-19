from django.contrib.auth.models import User
from rest_framework import authentication, exceptions

from config import models


class ApiUser(User):
    class Meta:
        abstract = True   # required for makemigrations to irgnore table?
        proxy = True

    def set_display(self, display):
        self._display = display

    def get_display(self):
        return self._display


class TokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        token = request.META.get('HTTP_X_DISPLAY')
        if not token:
            return None

        try:
            display = models.Display.objects.get(access_key=token)
            user = display.user
            user.qs_displays = models.Display.objects.filter(pk=display.id)
            user.qs_frames = models.Frame.objects.filter(display=display)
            user.qs_items = models.Item.objects.filter(frame__display=display)
            user.qs_finishings = models.Finishing.objects.filter(frame__display=display)
        except models.Display.DoesNotExist:
            raise exceptions.AuthenticationFailed('No such user')

        return (user, token)
