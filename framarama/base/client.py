
import requests

class ApiClient:

    def __init__(self, base_url, display_access_key):
        self._base_url = base_url.rstrip('/') + '/api'
        self._display_access_key = display_access_key

    def _request(self, path):
        _headers = {}
        _headers['X-Display'] = self._display_access_key
        _response = requests.get(self._base_url + path, headers=_headers)
        _response.raise_for_status()
        return _response.json()

    def get_display(self):
        _data = self._request('/displays')
        if 'results' in _data and len(_data['results']):
            return _data['results'][0]
        return None

    def get_items(self, display_id):
        return self._request('/displays/{}/items'.format(display_id))
        
