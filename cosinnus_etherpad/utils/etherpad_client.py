from builtins import str
from builtins import object
from functools import partial
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib.parse import urlencode
import requests


def utf8_encode(s):
    return s if isinstance(s, bytes) else s.encode('utf8')


def utf8_encode_dict_values(d):
    return {k: utf8_encode(v) for k, v in list(d.items())}


class EtherpadException(Exception): pass


class EtherpadLiteClient(object):

    def __init__(self, base_params={}, base_url='http://localhost:9001/api',
                       api_version='1', timeout=20, verify=True):
        self.api_version = api_version
        self.base_params = utf8_encode_dict_values(base_params)
        self.base_url = base_url
        self.timeout = timeout
        self.verify = verify

    def __call__(self, path, **params):
        params = utf8_encode_dict_values(params)
        data = urlencode(dict(self.base_params, **params))
        url = '%s/%s/%s?%s' % (self.base_url, self.api_version, path, data)
        try:
            resp = requests.get(url, data=data, verify=self.verify)
            r = resp.json()
        except Exception as e:
            raise EtherpadException('Error communicating with the Pad Server: %s' % str(e))
        
        if not r or not isinstance(r, dict):
            raise EtherpadException('API returned: %s' % r)
        if r.get('code') != 0:
            raise EtherpadException(r.get('message', r))
        return r.get('data')

    def __getattr__(self, name):
        return partial(self, name)
