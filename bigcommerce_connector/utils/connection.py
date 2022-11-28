from dataclasses import dataclass
from typing import Any
import requests


@dataclass
class RestfulConnection:
    
    scheme: str
    hostname: str
    uri: str
    url: str
    headers: dict
    data: Any
    params: dict
    json: dict
    
    def __post_init__(self):
        self.url = f"{self.scheme}{self.hostname}{self.uri}"
        
    def send(self, method, path, **kwargs):
        options = self.prepare_sending_options(**kwargs)
        res = self._send(method, path, **options)
        return res
    
    def prepare_sending_options(self, **kwargs):
        def update_kw_if_not_empty(key, value):
            if value:
                options[key] = value
        options = dict(**kwargs, timeout=(30, 60))
        for option_key in ('headers', 'params', 'data', 'json'):
            if hasattr(self, option_key):
                update_kw_if_not_empty(option_key, getattr(self, option_key))
        return options
    
    def _send(self, method, path, **kwargs):
        try:
            response = self._send_request(method, path, **kwargs)
            res = self._prepare_response(response)
        except Exception as e:
            pass
        return res
    
    def _send_request(self, method, path, **kwargs):
        url = f'{self.url}{path}'
        return requests.request(method, url, **kwargs)
    