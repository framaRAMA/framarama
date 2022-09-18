import logging

from django.db import models
from django.template import Context, Template

from framarama.base import forms as base
from config.models import SourceStep
from config.plugins import PluginImplementation
from config.forms.frame import CreateSourceStepForm, UpdateSourceStepForm
from config.utils import data


logger = logging.getLogger(__name__)

MIME_CHOICES = [
    ('auto', 'Auto (automatically detect mime type)'),
    ('text/csv', 'CSV (comma separated data)'),
    ('application/json', 'JSON'),
    ('text/plain','Plain text')
]

FIELDS = [
    'mime_in',
    'filter_in',
    'mime_out',
    'template_out',
]
WIDGETS = {
    'mime_in': base.selectFieldWidget(choices=MIME_CHOICES),
    'filter_in': base.charFieldWidget(),
    'mime_out': base.selectFieldWidget(choices=MIME_CHOICES),
    'template_out': base.textareaFieldWidget(),
}


class DataModel(SourceStep):
    source_ptr = models.OneToOneField(SourceStep, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    filter_in = models.CharField(
        max_length=256, blank=True,
        verbose_name='Input filter', help_text='Filter data using given expression (e.g. <a href="https://pypi.org/project/jsonpath-python/" target="_blank">JSONPath</a>, <a href="https://docs.python.org/3/library/xml.etree.elementtree.html#elementtree-xpath" target="_blank">XPath</a>)')
    template_out = models.TextField(
        blank=True,
        verbose_name='Output template', help_text='Write a simple Jinja2 template (the "data" variable contains filter result)')

    class Meta:
        managed = False


class DataCreateForm(CreateSourceStepForm):
    class Meta:
        model = DataModel
        fields = CreateSourceStepForm.fields(FIELDS)
        widgets = CreateSourceStepForm.widgets(WIDGETS)


class DataUpdateForm(UpdateSourceStepForm):
    class Meta:
        model = DataModel
        fields = UpdateSourceStepForm.fields(FIELDS)
        widgets = UpdateSourceStepForm.widgets(WIDGETS)


class Implementation(PluginImplementation):
    CAT = SourceStep.CAT_DATA
    TITLE = 'Data'
    DESCR = 'Process data (filter, convert)'
    
    Model = DataModel
    CreateForm = DataCreateForm
    UpdateForm = DataUpdateForm

    def run(self, model, data_in, ctx):
        _data_out = data_in.copy()

        if model.filter_in:
            _data_out = _data_out.filter(model.filter_in)
        
        if model.template_out:
            _template = Template(model.template_out)
            _output = _template.render(Context({'data': _data_out.get_as_dict().get()}))
            
            _data_out = data.DataContainer(data=_output, data_type=data.DataType(DataType.MIME, model.mime_out))
        
        return [_data_out]

