import requests

from config import models as config_models
from framarama.base.utils import Singleton, Config

class ApiResult:

    def __init__(self, data, mapper):
        self._data = data
        self._mapper = mapper

    def _map(self, data):
        return self._mapper(data)


class ApiResultItem(ApiResult):

    def __init__(self, data, mapper):
        super().__init__(data, mapper)
        self._item = None

    def get(self, name, default=None):
        return self._data.get(name, default) if self._data else None

    def item(self):
        if self._data is None:
            return None
        if self._item is None:
            self._item = self._map(self._data)
        return self._item


class ApiResultList(ApiResult):

    def __init__(self, data, mapper):
        super().__init__(data, mapper)
        self._items = None

    def count(self):
        return self._data.get('count', 0) if self._data else None

    def items(self):
        if self._data is None:
            return None
        if self._items is None:
            self._items = [self._map(_item) for _item in self._data['results']]
        return self._items

    def get(self, index):
        return self.items()[index]


class ApiClient(Singleton):

    def __init__(self):
        super().__init__()
        self._base_url = None
        self._display_access_key = None
        _config = Config.get().get_config()
        if _config:
            if _config.mode == 'local':
                self._base_url = 'http://127.0.0.1:8000'
            else:
                self._base_url = _config.cloud_server
            self._display_access_key = _config.cloud_display_access_key
            self._base_url = self._base_url.rstrip('/') + '/api'
            self._display_access_key = self._display_access_key

    def configured(self):
        return self._base_url != None and self._display_access_key != None

    def _request(self, path):
        if not self.configured():
            raise Exception("API client not configured")
        _headers = {}
        _headers['X-Display'] = self._display_access_key
        _response = requests.get(self._base_url + path, headers=_headers)
        _response.raise_for_status()
        return _response.json()

    def _list(self, mapper):
        _data = ApiResultList()
        return _data

    def get_display(self):
        _data = self._request('/displays')
        if _data and 'results' in _data and len(_data['results']):
            return ApiResultItem(
                _data['results'][0],
                lambda d: config_models.Display(**{k: v for k, v in d.items() if k not in ['device_type_name', 'frame']}))
        return None

    def get_items_list(self, display_id):
        return ApiResultList(
            self._request('/displays/{}/items/all'.format(display_id)),
            lambda d: config_models.Item(**{k: v for k, v in d.items() if k not in ['rank']}))

    def get_items_next(self, display_id):
        _result = ApiResultList(
            self._request('/displays/{}/items/next'.format(display_id)),
            lambda d: config_models.Item(**{k: v for k, v in d.items() if k not in ['rank']}))
        return _result.get(0) if _result.count() > 0 else None

    def get_finishings(self, display_id):
        return ApiResultList(
            self._request('/displays/{}/finishings'.format(display_id)),
            lambda d: config_models.Finishing(**d))



