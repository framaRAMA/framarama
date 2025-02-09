import base64
import typing

from django.conf import settings
from rest_framework import serializers

from api.views import config as config_views
from config import models as config_models
from framarama.base.utils import Singleton, Config, Network
from framarama.base.models import BaseModel

class ApiResult:

    def __init__(self, data: dict, mapper: typing.Callable[[dict], object]):
        self._data = data
        self._mapper = mapper

    def _map(self, data: dict) -> object:
        if data is None:
            return None
        return self._mapper(data)

    def get(self, name: str, default=None):
        return self._data.get(name, default) if self._data else None


class ApiResultItem(ApiResult):

    def __init__(self, data: dict, mapper: typing.Callable[[dict], object]):
        super().__init__(data, mapper)
        self._item = None

    def get_link(self, name: str, default=None) -> str:
        for _link in self.get('links'):
            if _link['rel'] == name:
                return _link['href']
        return default

    def item(self) -> object:
        if self._item is None:
            self._item = self._map(self._data)
        return self._item


class ApiResultList(ApiResult):

    def __init__(self, data: dict, mapper: typing.Callable[[dict], object]):
        super().__init__(data, mapper)
        self._items = None

    def count(self) -> int:
        return self.get('count', 0)

    def items(self) -> typing.List[ApiResultItem]:
        if self._items is None:
            self._items = [ApiResultItem(_item, self._map) for _item in self.get('results')]
        return self._items

    def item(self, index: int) -> ApiResultItem:
        return self.items()[index]


class ApiClient(Singleton):
    METHOD_GET = Network.METHOD_GET
    METHOD_POST = Network.METHOD_POST
    METHOD_PUT = Network.METHOD_PUT
    METHOD_HEAD = Network.METHOD_HEAD

    def __init__(self):
        super().__init__()
        self._base_url = None
        self._display_access_key = None
        self._user_agent = {'v': None, 'd': None}
        _config = Config.get().get_config()
        if _config:
            if _config.mode == 'local':
                self._base_url = settings.FRAMARAMA['API_URL']
            else:
                self._base_url = _config.cloud_server
            self._display_access_key = _config.cloud_display_access_key
            self._base_url = self._base_url.rstrip('/') + '/api'

    def register_user_agent(self, _type: str, _value: str):
        self._user_agent[_type] = _value

    def configured(self) -> bool:
        return self._base_url != None and self._display_access_key != None

    def _http(self, url: str, method: str, data: str|None=None, headers: dict|None=None, **kwargs) -> object:
        return Network.get_url(url, method, data, headers, self._user_agent, **kwargs)

    def _request(self, path: str, method: str=METHOD_GET, data:str|None=None, raw:bool=False, **kwargs) -> object:
        if not self.configured():
            raise Exception("API client not configured")
        _response = self._http(self._base_url + path, method, data, {'X-Display': self._display_access_key}, **kwargs)
        _response.raise_for_status()
        return _response if raw else _response.json()

    def _map(self, data: dict, model, serializer: serializers.ModelSerializer|None=None) -> object:
        _fields = [_field.name for _field in model._meta.fields]
        _model_fields = {k: v for k, v in data.items() if k in _fields}
        _additional_fields = {k: v for k, v in data.items() if k not in _fields}
        if serializer:
            _serializer = serializer(data=_model_fields)
            _serializer.is_valid()
            _model = _serializer.map(_model_fields, _serializer.validated_data)
        else:
            _model = model(**_model_fields)  # doesnt work w/ serializer for nested fields (field must contain object directly, no dict)
        _model._additional_fields = _additional_fields
        return _model

    def _list(self, data: dict, model: BaseModel, serializer: serializers.ModelSerializer|None=None) -> ApiResultList:
        return ApiResultList(data, lambda d: self._map(d, model, serializer))

    def _item(self, data: dict, model: BaseModel, serializer: serializers.ModelSerializer|None=None) -> ApiResultItem:
        return ApiResultItem(data, lambda d: self._map(d, model, serializer))

    def get_url(self, url: str, method: str=METHOD_GET, data: dict|None=None, headers: dict|None=None, **kwargs) -> object:
        if url.startswith(self._base_url):
            return self._request(url[len(self._base_url):], method, data, True, **kwargs)
        else:
            return self._http(url, method, data, headers, **kwargs)

    def get_display(self) -> ApiResultItem:
        _data = self._request('/displays')
        if _data and 'results' in _data and len(_data['results']):
            return self._item(_data['results'][0], config_models.Display, config_views.DisplaySerializer)
        return None

    def get_item(self, display_id: int, item_id: int) -> ApiResultItem:
        return self._item(
            self._request('/displays/{}/items/all/{}'.format(display_id, item_id)),
            config_models.Item, config_views.ItemDisplaySerializer)

    def get_item_download(self, display_id: int, item_id: int) -> bytes:
        return self._request('/displays/{}/items/all/{}/download'.format(display_id, item_id), raw=True).content

    def get_items_list(self, display_id: int) -> ApiResultList:
        return self._list(
            self._request('/displays/{}/items/all'.format(display_id)),
            config_models.Item, config_views.ItemDisplaySerializer)

    def get_items_next(self, display_id: int) -> ApiResultItem:
        _data = self._request('/displays/{}/items/next'.format(display_id))
        _result = self._list(_data, config_models.RankedItem, config_views.RankedItemDisplaySerializer)
        return _result.item(0) if _result.count() > 0 else None

    def submit_item_hit(self, display_id: int, data: dict, thumbnail: bytes|None=None, mime: str|None=None, meta: str|None=None) -> object:
        if thumbnail or mime:
            _thumbnail = {}
            if thumbnail:
                _thumbnail['data'] = base64.b64encode(thumbnail).decode()
            if mime:
                _thumbnail['mime'] = mime
            if meta:
                _thumbnail['meta'] = meta
            data['thumbnail'] = _thumbnail
        self._request('/displays/{}/items/hits'.format(display_id), ApiClient.METHOD_POST, data)

    def get_contexts(self, display_id: int) -> ApiResultList:
        return self._list(
            self._request('/displays/{}/contexts'.format(display_id)),
            config_models.FrameContext, config_views.ContextDisplaySerializer)

    def get_finishings(self, display_id: int) -> ApiResultList:
        return self._list(
            self._request('/displays/{}/finishings'.format(display_id)),
            config_models.Finishing, config_views.FinishingDisplaySerializer)

    def get_setting_variables(self) -> ApiResultList:
        return self._list(
            self._request('/settings/vars'),
            config_models.Settings, config_views.SettingsSerializer)

    def submit_status(self, display_id: int, status: dict) -> ApiResultList:
        return self._request('/displays/{}/status'.format(display_id), ApiClient.METHOD_POST, status)


