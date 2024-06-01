import logging

from django import forms

from framarama.base import forms as base
from config.models import Sorting
from config.plugins import SortingPluginImplementation
from config.forms.frame import SortingForm


logger = logging.getLogger(__name__)


class CustomForm(SortingForm):
    code = forms.CharField(
        label='Query', help_text='Custom query to execute to generate a rank value', widget=base.customSortingQueryFieldWidget())

    class Meta(SortingForm.Meta):
        entangled_fields = {'plugin_config': ['code']}

    field_order = SortingForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(SortingPluginImplementation):
    CAT = Sorting.CAT_CUSTOM
    TITLE = 'Custom'
    DESCR = 'Specify a custom query'
    
    Form = CustomForm
    
    def run(self, model, context):
        _code = model.plugin_config.get('code', '')

        return _code


