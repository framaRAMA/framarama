
from django.contrib.auth import forms as auth_forms

from framarama.base import forms as base


class AuthenticationForm(base.BaseForm, auth_forms.AuthenticationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['password'].widget.attrs['class'] = 'form-control'


