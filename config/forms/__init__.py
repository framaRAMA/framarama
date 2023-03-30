
from django import forms
from django.contrib.auth import forms as auth_forms, get_user_model

from framarama.base import forms as base


class AuthenticationForm(base.BaseForm, auth_forms.AuthenticationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['password'].widget.attrs['class'] = 'form-control'


class UpdateProfileForm(base.BaseModelForm):
    username = forms.CharField(disabled=True, widget=base.charFieldWidget())

    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'first_name': base.charFieldWidget(),
            'last_name': base.charFieldWidget(),
            'email': base.charFieldWidget(),
        }


