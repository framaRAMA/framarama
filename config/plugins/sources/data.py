import logging

from django import forms

from framarama.base import forms as base, utils
from config.models import SourceStep
from config.plugins import SourcePluginImplementation
from config.forms.frame import SourceStepForm
from config.utils import data


logger = logging.getLogger(__name__)


class DataForm(SourceStepForm):
    filter_in = forms.CharField(
        max_length=256, required=False, widget=base.charFieldWidget(),
        label='Input filter', help_text='Filter data using given expression (e.g. <a href="https://pypi.org/project/jsonpath-python/" target="_blank">JSONPath</a>, <a href="https://docs.python.org/3/library/xml.etree.elementtree.html#elementtree-xpath" target="_blank">XPath</a>)')
    template_out = forms.CharField(
        required=False, widget=base.textareaFieldWidget(),
        label='Output template', help_text='Write a simple Jinja2 template (the "data" variable contains filter result)')

    class Meta(SourceStepForm.Meta):
        entangled_fields = {'plugin_config': ['filter_in', 'template_out']}

    field_order = SourceStepForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(SourcePluginImplementation):
    CAT = SourceStep.CAT_DATA
    TITLE = 'Data'
    DESCR = 'Process data (filter, convert)'
    
    Form = DataForm

    def run(self, model, data_in, ctx):
        _filter_in = model.plugin_config.get('filter_in')
        _template_out = model.plugin_config.get('template_out')
        _mime_out = model.mime_out

        _data_out = data_in.copy()

        if _filter_in:
            _data_out = _data_out.filter(_filter_in)
        
        if _template_out:
            _data_out_dict = _data_out.get_as_dict()
            _output = utils.Template.render(_template_out, globals_vars={'data': _data_out_dict.get() if _data_out_dict else {}})
            
            _data_out = data.DataContainer(data=_output, data_type=data.DataType(data.DataType.MIME, _mime_out))
        
        return [_data_out]

