import re
import ast
import logging

from django import forms
from django.core.exceptions import ValidationError

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

    def clean_code(self):
        _code = self.cleaned_data['code']
        try:
            ast.parse(re.sub(r"[\r\n]+\s*", "", _code))  # fix indent by removing newline/whitespaces)
        except SyntaxError as e:
            raise ValidationError('Invalid code: {}'.format(e))
        return _code


class Implementation(SortingPluginImplementation):
    CAT = Sorting.CAT_CUSTOM
    TITLE = 'Custom'
    DESCR = 'Specify a custom query'
    
    Form = CustomForm
    
    def run(self, model, config, context):
        _code = config.code.as_str()

        return _code


