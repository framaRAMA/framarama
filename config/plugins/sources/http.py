import cgi
import json
import requests
import logging

from django import forms

from framarama.base import forms as base, api
from config.models import SourceStep
from config.plugins import SourcePluginImplementation
from config.forms.frame import SourceStepForm
from config.utils import data


logger = logging.getLogger(__name__)

METHOD_CHOICES = [
  ('GET', 'GET Request'),
  ('POST', 'POST Request'),
  ('PUT', 'PUT Request'),
  ('HEAD', 'HEAD Request')
]


class HttpForm(SourceStepForm):
    url = forms.URLField(
        max_length=1024, widget=base.charFieldWidget(),
        label='Address (URL)', help_text='Enter the complete address (URL) to load')
    url_formatted = forms.BooleanField(
        initial=False, required=False, widget=base.booleanFieldWidget(),
        label='URL includes format tokens')
    method = forms.CharField(
        max_length=16, initial='GET', widget=base.selectFieldWidget(choices=METHOD_CHOICES),
        label='Type', help_text='Specify the type of the request (defaults to GET)')
    body = forms.CharField(
        required=False, widget=base.textareaFieldWidget(),
        label='Content')
    body_type = forms.CharField(
        max_length=64, required=False, widget=base.charFieldWidget(),
        label='Content type', help_text='Content (body) and Content-Type to send with request')
    body_formatted = forms.BooleanField(
        initial=False, required=False, widget=base.booleanFieldWidget(),
        label='Body includes format tokens')
    auth_user = forms.CharField(
        max_length=64, required=False, widget=base.charFieldWidget(),
        label='Username', help_text='Username to use for authentication (basic auth)')
    auth_pass = forms.CharField(
        max_length=64, required=False, widget=base.charFieldWidget(),
        label='Password', help_text='Password to use for authentication (basic auth)')
    headers = forms.CharField(
        initial="{\n}\n", widget=base.textareaFieldWidget(),
        label='Headers', help_text='Specify additional headers in JSON structure (key=header name, value=header value)')

    class Meta(SourceStepForm.Meta):
        entangled_fields = {'plugin_config': ['url', 'url_formatted', 'method', 'body', 'body_type', 'body_formatted', 'auth_user', 'auth_pass', 'headers']}

    field_order = SourceStepForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(SourcePluginImplementation):
    CAT = SourceStep.CAT_NETWORK
    TITLE = 'HTTP'
    DESCR = 'Fetch data using HTTP protocol'
    
    Form = HttpForm
    
    def __init__(self):
        self._cookies = {}

    def _args(self, model, config, data_in):
        _url = config.url.as_str()
        _url_formatted = config.url_formatted.as_str()
        _method = config.method.as_str()
        _body = config.body.as_str()
        _body_formatted = config.body_formatted.as_str()
        _body_type = config.body_type.as_str()
        _auth_user = config.auth_user.as_str()
        _auth_pass = config.auth_pass.as_str()
        _headers = config.headers.as_str()

        _api_methods = {
            'GET': api.ApiClient.METHOD_GET,
            'POST': api.ApiClient.METHOD_POST,
            'PUT': api.ApiClient.METHOD_PUT,
            'HEAD': api.ApiClient.METHOD_HEAD,
        }
        _data = data_in.get_as_dict()
        _args = {}
        _args["url"] = self.format_field(_url, _url_formatted, _data.get() if _data else {})
        _args["method"] = _api_methods[_method] if _method in _api_methods else api.ApiClient.METHOD_GET
        _args["cookies"] = self._cookies
        _args["headers"] = {}

        if _body:
          _args["data"] = self.format_field(_body, _body_formatted, _data)
        
        if _body_type:
          _args["headers"]["Content-Type"] = _body_type

        if _auth_user:
            _args["auth"] = (_auth_user, _auth_pass)

        #if _headers:
        #    _args["headers"] = _headers

        return _args

    def run(self, model, config, data_in, ctx):
        _args = self._args(model, config, data_in)
        logger.info("Loading {}".format(_args["url"]))
        _response = api.ApiClient.get().get_url(**_args)
        if _response:
            _content_type = _response.headers['content-type'] if 'content-type' in _response.headers else None
            _mime_type = cgi.parse_header(_content_type)[0] if _content_type is not None else None

            self._cookies.update(requests.utils.dict_from_cookiejar(_response.cookies))

            return [data.DataContainer(_response.content, data_type=data.DataType(data.DataType.MIME, _mime_type), conv=data.NoopDataConverter())]
        else:
            logger.error("Request returned non-success status code: {}".format(_response))

        return []

