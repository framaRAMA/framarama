import logging

from django import forms

from config.models import Finishing
from config.plugins import FinishingPluginImplementation
from config.forms.frame import FinishingForm

from framarama.base import forms as base


logger = logging.getLogger(__name__)


class VariableForm(base.BaseForm):
    TITLE = 'Variable'
    var_name = forms.CharField(label='Name', help_text='Name of variable (prefixed with "globals.$name")', widget=base.charFieldWidget())
    var_value = forms.CharField(label='Value', help_text='The value of variable', widget=base.charFieldWidget())


class GroupForm(FinishingForm):
    name = forms.CharField(label='Name', required=False, help_text='Name of group (use for variable prefix)', widget=base.charFieldWidget())

    dependencies = {}

    class Meta(FinishingForm.Meta):
        untangled_fields = [_f for _f in FinishingForm.Meta.untangled_fields if _f not in ['image_in', 'image_out']]
        entangled_fields = {'plugin_config': ['name']}

    field_order = Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class VariablesGroupForm(base.BaseChainedForm):

    def __init__(self, data=None, instance=None, *args, **kwargs):
        _initial = [{'var_name': _k, 'var_value': _v} for _k, _v in instance.plugin_config.get('variables', {}).items()] if instance is not None else []
        super().__init__([
            GroupForm(data=data, instance=instance),
            forms.formset_factory(VariableForm, extra=0 if _initial else 1)(data=data, initial=_initial)
        ])

    def save(self, *args, **kwargs):
        _model_form, _var_forms = self.chain()
        _group = _model_form.save(commit=False, *args, **kwargs)
        _group.plugin_config['variables'] = {
            _var_form.cleaned_data['var_name']: _var_form.cleaned_data['var_value']
            for _var_form in _var_forms.forms
            if 'var_name' in _var_form.cleaned_data
        }
        _group.save()
        return _group


class Implementation(FinishingPluginImplementation):
    CAT = Finishing.CAT_GROUP
    TITLE = 'Group'
    DESCR = 'Group elements'
    
    Form = VariablesGroupForm

    def enter(self, model, config, ctx):
        if 'variables' in config:
            ctx.push_variables(config['variables'], config['name'])

    def leave(self, model, config, ctx):
        if 'variables' in config:
            ctx.pop_variables(config['name'])
    
    def run(self, model, config, image, ctx):
        return image

