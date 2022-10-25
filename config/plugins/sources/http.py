import cgi
import json
import requests
import logging

from django.db import models

from framarama.base import forms as base
from config.models import SourceStep
from config.plugins import PluginImplementation
from config.forms.frame import CreateSourceStepForm, UpdateSourceStepForm
from config.utils import data


logger = logging.getLogger(__name__)

METHOD_CHOICES = [('GET', 'GET Request'), ('POST', 'POST Request'), ('PUT', 'PUT Request'), ('HEAD', 'HEAD Request')]

FIELDS = [
    'url_formatted',
    'url',
    'method',
    'body_formatted',
    'body',
    'body_type',
    'auth_user',
    'auth_pass',
    'headers',
]
WIDGETS = {
    'url_formatted': base.booleanFieldWidget(),
    'url': base.charFieldWidget(),
    'method': base.selectFieldWidget(choices=METHOD_CHOICES),
    'body_formatted': base.booleanFieldWidget(),
    'body': base.textareaFieldWidget(),
    'body_type': base.charFieldWidget(),
    'auth_user': base.charFieldWidget(),
    'auth_pass': base.charFieldWidget(),
    'headers': base.textareaFieldWidget(),
}


class HttpModel(SourceStep):
    source_ptr = models.OneToOneField(SourceStep, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    url = models.URLField(
        max_length=1024,
        verbose_name='Address (URL)', help_text='Enter the complete address (URL) to load')
    url_formatted = models.BooleanField(
        default=False,
        verbose_name='URL includes format tokens')
    method = models.CharField(
        max_length=16, choices=METHOD_CHOICES, default='GET',
        verbose_name='Type', help_text='Specify the type of the request (defaults to GET)')
    body = models.TextField(
        blank=True,
        verbose_name='Content')
    body_type = models.CharField(
        max_length=64, blank=True,
        verbose_name='Content type', help_text='Content (body) and Content-Type to send with request')
    body_formatted = models.BooleanField(
        default=False,
        verbose_name='Body includes format tokens')
    auth_user = models.CharField(
        max_length=64, blank=True,
        verbose_name='Username', help_text='Username to use for authentication (basic auth)')
    auth_pass = models.CharField(
        max_length=64, blank=True,
        verbose_name='Password', help_text='Password to use for authentication (basic auth)')
    headers = models.TextField(
        default="{\n}\n",
        verbose_name='Headers', help_text='Specify additional headers in JSON structure (key=header name, value=header value)')

    class Meta:
        managed = False


class HttpCreateForm(CreateSourceStepForm):
    class Meta:
        model = HttpModel
        fields = CreateSourceStepForm.fields(FIELDS)
        widgets = CreateSourceStepForm.widgets(WIDGETS)


class HttpUpdateForm(UpdateSourceStepForm):
    class Meta:
        model = HttpModel
        fields = UpdateSourceStepForm.fields(FIELDS)
        widgets = UpdateSourceStepForm.widgets(WIDGETS)


class Implementation(PluginImplementation):
    CAT = SourceStep.CAT_NETWORK
    TITLE = 'HTTP'
    DESCR = 'Fetch data using HTTP protocol'
    
    Model = HttpModel
    CreateForm = HttpCreateForm
    UpdateForm = HttpUpdateForm
    
    def __init__(self):
        self._cookies = {}

    def _args(self, model, data_in):
        _data = data_in.get_as_dict()
        _args = {}
        _args["url"] = self.format_field(model.url, model.url_formatted, _data.get() if _data else {})
        _args["method"] = model.method
        _args["cookies"] = self._cookies
        _args["headers"] = {}

        if model.body:
          _args["data"] = self.format_field(model.body, model.body_formatted, _data)
        
        if model.body_type:
          _args["headers"]["Content-Type"] = model.body_type

        if model.auth_user:
            _args["auth"] = (model.auth_user, model.auth_pass)

        #if model.headers:
        #    _args["headers"] = model.headers

        return _args

    def run(self, model, data_in, ctx):
        _args = self._args(model, data_in)
        logger.info("Loading {}".format(_args["url"]))
        _response = requests.request(**_args)
        if _response:
            _content_type = _response.headers['content-type'] if 'content-type' in _response.headers else None
            _mime_type = cgi.parse_header(_content_type)[0] if _content_type is not None else None

            self._cookies.update(requests.utils.dict_from_cookiejar(_response.cookies))

            logger.debug(_mime_type)
            logger.debug(_response.content)
            return [data.DataContainer(_response.content, data_type=data.DataType(data.DataType.MIME, _mime_type), conv=data.NoopDataConverter())]
        else:
            logger.error("Request returned non-success status code: {}".format(_response))

        return []

