import logging

from django import forms

from framarama.base import forms as base
from config.models import FrameContext
from config.plugins import ContextPluginImplementation
from config.forms.frame import ContextForm
from config.utils import context


logger = logging.getLogger(__name__)


class VariablesForm(ContextForm):
    variables = forms.JSONField(
        required=False, initial=dict, widget=base.textareaFieldWidget(),
        label='Variables', help_text='Key/value pairs to provied as global variables')

    class Meta(ContextForm.Meta):
        entangled_fields = {'plugin_config': ['variables']}

    field_order = ContextForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(ContextPluginImplementation):
    CAT = FrameContext.CAT_VARS
    TITLE = 'Variables'
    DESCR = 'Global variables'

    Form = VariablesForm

    def run(self, model, config, image, ctx):
        return {config.name.as_str(): context.EvaluatedResolver(ctx, context.MapResolver(config.variables))}

