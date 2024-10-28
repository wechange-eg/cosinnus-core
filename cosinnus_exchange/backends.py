import json
import logging
import urllib.parse
from datetime import datetime
from importlib import import_module

import requests
from django.apps import apps
from haystack.query import SearchQuerySet

from cosinnus.conf import settings

logger = logging.getLogger(__name__)


class ExchangeError(Exception):
    pass


class ExchangeBackend:
    url = None
    token_url = None
    username = None
    password = None
    accept_language = None
    model = None
    serializer = None
    source = None

    token = None
    expires_in = None

    def __init__(
        self,
        url,
        model,
        serializer,
        serializer_kwargs=None,
        source=None,
        token_url=None,
        username=None,
        password=None,
        accept_language=None,
    ):
        self.url = url
        self.token_url = token_url or f"{'/'.join(url.split('/')[:-2])}/token/"
        self.username = username
        self.password = password
        self.accept_language = accept_language
        self.source = source or urllib.parse.urlparse(url).netloc
        self.model = apps.get_model(*model.rsplit('.'))
        serializer_module_name, serializer_name = serializer.rsplit('.', 1)
        serializer_module = import_module(serializer_module_name)
        if not serializer_kwargs:
            serializer_kwargs = {}
        serializer_kwargs['source'] = self.source
        self.serializer = getattr(serializer_module, serializer_name)(**serializer_kwargs)

    def pull(self):
        """
        Pull data from backend
        :return:
        """
        results = self._get()
        indexed = self._get_indexed_ids()
        self._create(results)
        self._delete_stale(indexed, results)

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
        if not self.username or not self.password:
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
        self.token = data['access']
        self.expires_in = None  # datetime.now() + timedelta(seconds=data['expiresIn'])

    def _serialize_results(self, results):
        serialized_results = []
        for result in results:
            try:
                serialized_result = self.serializer.to_representation(instance=result)
                serialized_results.append(serialized_result)
                if settings.DEBUG:
                    print(f'>> pulled: {serialized_result.get("url")}')
            except Exception as e:
                logger.warn(
                    'An external data object could not be pulled in for cosinnus exchange!',
                    extra={'page_result': result, 'exception': str(e)},
                )
                if settings.DEBUG:
                    print(f'>> Error: {result.get("url", result.get("slug"))}')
                    raise
        return serialized_results

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
        if self.accept_language:
            headers['Accept-Language'] = self.accept_language
        next_url = self.url
        while next_url:
            response = requests.get(next_url, headers=headers)
            try:
                response.raise_for_status()
            except requests.HTTPError:
                raise ExchangeError(response.status_code, next_url, response.content)

            data = json.loads(response.content)
            if 'next' in data:
                # paginated results
                page_results = self._serialize_results(data['results'])
                results += page_results
                next_url = data['next']
            else:
                # non-paginated results
                results = self._serialize_results(data)
                next_url = None
        return results

    def _create(self, results):
        """
        Create objects in ElasticSearch index
        """
        for data in results:
            obj = self.model(**data)
            obj.save()

    def _get_indexed_ids(self):
        """
        Returns the IDs of currently indexed results for the backends model and source.
        Note: Using "pk" as it contains the url/slug of the instance, while "id" has the additional model-name prefix.
        """
        sqs = SearchQuerySet().models(self.model).filter(source=self.source).all()
        ids = [result.pk for result in sqs]
        return ids

    def _delete_stale(self, indexed_ids, results):
        """
        Deletes stale results from the index by comparing the initially indexed ids with the results.
        Note: The ID of a ExchangeObjectBaseModel instance is set to the result "url" so we use it here.
        """
        created_ids = [result.get('url') for result in results]
        stale_ids = set(indexed_ids).difference(set(created_ids))
        for stale_id in stale_ids:
            self.model(url=stale_id).remove_index()
            if settings.DEBUG:
                print(f'>> deleted stale: {stale_id}')
