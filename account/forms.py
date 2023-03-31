
from django import forms
from django.contrib.auth import forms

from account import models


class UserCreationForm(forms.UserCreationForm):

    class Meta:
        model = models.User
        fields = ("username", "email")


class UserChangeForm(forms.UserChangeForm):

    class Meta:
        model = models.User
        fields = ("username", "email")

