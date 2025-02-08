import json

from django import forms
from django.forms.models import inlineformset_factory
from entangled.forms import EntangledModelFormMixin

from config import models
from config.forms.base import BasePluginForm, TreeBasePluginForm
from framarama.base import forms as base


class SettingsForm(EntangledModelFormMixin, base.BaseModelForm):
    class Meta:
        model = models.Settings
        fields = ['name']
        widgets = {
            'name': base.charFieldWidget()
        }
        untangled_fields = ['name']


class VariableForm(base.BaseForm):
    TITLE = 'Variable'
    var_name = forms.CharField(label='Name', help_text='Name of variable', widget=base.charFieldWidget())
    var_value = forms.CharField(label='Value', help_text='The value of variable', widget=base.charFieldWidget())


class VariablesSettingsForm(base.BaseChainedForm):

    def __init__(self, data=None, instance=None, *args, **kwargs):
        _initial = [{'var_name': _k, 'var_value': _v} for _k, _v in instance.properties.items()] if instance is not None else []
        super().__init__([
            SettingsForm(data=data, instance=instance),
            forms.formset_factory(VariableForm, extra=0 if _initial else 1)(data=data, initial=_initial)
        ])

    def save(self, *args, **kwargs):
        _model_form, _var_forms = self.chain()
        _settings = _model_form.save(commit=False, *args, **kwargs)
        _settings.properties = {
            _var_form.cleaned_data['var_name']: _var_form.cleaned_data['var_value']
            for _var_form in _var_forms.forms
            if 'var_name' in _var_form.cleaned_data
        }
        _settings.save()
        return _settings

