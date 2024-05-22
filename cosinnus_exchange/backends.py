import json
import logging
import urllib.parse
from datetime import datetime
from importlib import import_module

import requests
from django.apps import apps

from cosinnus.conf import settings

logger = logging.getLogger(__name__)


class ExchangeError(Exception):
    pass


class ExchangeBackend:
    url = None
    token_url = None
    username = None
    password = None
    model = None
    serializer = None
    source = None

    token = None
    expires_in = None

    def __init__(self, url, model, serializer, source=None, token_url=None, username=None, password=None):
        self.url = url
        self.token_url = token_url or f"{'/'.join(url.split('/')[:-2])}/token/"
        self.username = username
        self.password = password
        self.source = source or urllib.parse.urlparse(url).netloc
        self.model = apps.get_model(*model.rsplit('.'))
        serializer_module_name, serializer_name = serializer.rsplit('.', 1)
        serializer_module = import_module(serializer_module_name)
        self.serializer = getattr(serializer_module, serializer_name)(source=self.source)

    def pull(self):
        """
        Pull data from backend
        :return:
        """
        results = self._get()
        self._delete()
        self._create(results)

    def authenticate(self):
        """
        Authenticate if no token or token expired
        """
        if not self.token:
            self._authenticate()
        elif self.expires_in < datetime.now():
            self._authenticate()

    def _authenticate(self):
        """
        Authenticate with backend if user/password given
        :return:
        """
        if not self.username and not self.password:
            return
        params = {
            'username': self.username,
            'password': self.password,
        }
        response = requests.post(self.token_url, params)
        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise ExchangeError(response.status_code, response.content)
        if not response.content:
            # No content, but no HTTP error
            return True
        try:
            data = json.loads(response.content)
        except ValueError:
            raise ExchangeError(response.status_code, response.content)
        if 'errors' in data:
            raise ExchangeError(response.status_code, response.content)
        self.token = data['token']
        self.expires_in = None  # datetime.now() + timedelta(seconds=data['expiresIn'])

    def _get(self):
        """
        Pull data from backend
        :return: serialized data
        """
        results = []

        self.authenticate()
        headers = {'Accept': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        next_url = self.url
        while next_url:
            response = requests.get(next_url, headers=headers)
            try:
                response.raise_for_status()
            except requests.HTTPError:
                raise ExchangeError(response.status_code, next_url, response.content)

            data = json.loads(response.content)
            page_results = []
            for page_result in data['results']:
                try:
                    page_results.append(self.serializer.to_representation(instance=page_result))
                    if settings.DEBUG:
                        print(f'>> pulled: {page_result.get("url")}')
                except Exception as e:
                    logger.warn(
                        'An external data object could not be pulled in for cosinnus exchange!',
                        extra={'page_result': page_result, 'exception': str(e)},
                    )
                    if settings.DEBUG:
                        print(f'>> Error: {page_result.get("url")}')
                        raise
            results += page_results
            next_url = data['next']
        return results

    def _create(self, results):
        """
        Create objects in ElasticSearch index
        """
        for data in results:
            obj = self.model(**data)
            obj.save()

    def _delete(self):
        """
        Delete existing data for model in ElasticSearch index
        FIXME: Use _delete_by_query once we've upgraded to ES>=5
        :return:
        """
        pass
