
from django import forms

from config import models
from framarama.base import forms as base


class SettingsForm(base.BaseModelForm):
    class Meta:
        model = models.Settings
        fields = ['name']
        widgets = {
            'name': base.charFieldWidget()
        }


class InternalUserSettingsForm(SettingsForm):
    version_fix = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='Version', help_text='List of valid versions to use for this user - see PEP-0404')

    class Meta(SettingsForm.Meta):
        entangled_fields = {'properties': ['version_fix']}


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

