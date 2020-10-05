import json
import logging
from datetime import datetime, timedelta
from importlib import import_module

import requests
from django.conf import settings
from django.apps import apps

logger = logging.getLogger(__name__)


class GoodDBError(Exception):
    pass


class GoodDBConnection:

    _base_url = None
    _user = None
    _password = None

    _access_token = None
    _expires_in = None

    def __init__(self, user=settings.COSINNUS_GOODDB_USER, password=settings.COSINNUS_GOODDB_PASSWORD,
                 url=settings.COSINNUS_GOODDB_BASE_URL):
        self._base_url = url
        self._user = user
        self._password = password

    def authenticate(self):
        if not self._access_token:
            self._authenticate()
        elif self._expires_in < datetime.now():
            self._authenticate()

    def _authenticate(self):
        """
        :return:
        """
        params = {
            'username': self._user,
            'password': self._password,
        }
        response = requests.post(f'{self._base_url}/login', params)
        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise GoodDBError(response.status_code, response.content)
        if not response.content:
            # No content, but no HTTP error
            return True
        try:
            data = json.loads(response.content)
        except ValueError:
            raise GoodDBError(response.status_code, response.content)
        if 'errors' in data:
            raise GoodDBError(response.status_code, response.content)
        self._access_token = data['access_token']
        self._expires_in = datetime.now() + timedelta(seconds=data['expiresIn'])

    def _push(self, path, queryset, serializer, key='items'):
        """
        Push given queryset data to GoodDB
        :return:
        """
        headers = {
            'Authorization': 'Bearer %s' % self._access_token,
            'Accept': 'application/json'
        }
        # self.authenticate()

        serializer = serializer()
        offset, limit = 0, 100
        count = queryset.count()
        while offset < count:
            # Get items
            items = [serializer.to_representation(instance=e) for e in queryset.all()[offset:offset + limit]]
            self._push(path, {key: items})
            offset += limit

            # Push items
            response = requests.put(f'{self._base_url}{path}', data={key: items}, headers=headers)
            try:
                response.raise_for_status()
            except requests.HTTPError:
                raise GoodDBError(response.status_code, response.content)

    def push(self):
        """
        Push all registered models to GoodDB
        :return:
        """
        for name, config in settings.COSINNUS_GOODDB_PUSH.items():
            # Resolve model
            app_label, model_name = config['model'].rsplit('.')
            model = apps.get_model(app_label, model_name)

            # Resolve serializer
            serializer_module_name, serializer_name = config['model'].rsplit('.')
            serializer_module = import_module(serializer_module_name)
            serializer = getattr(serializer_module, serializer_name)

            # Create (public but not synced)
            queryset = model.objects.gooddb_create()
            self._push(config['path'], queryset, serializer, name)
            # Update (public, synced and modified since last run)
            queryset = model.objects.gooddb_update()
            self._push(config['path'], queryset, serializer, name)
            # Delete (not public but synced)
            queryset = model.objects.gooddb_delete()
            self._push(config['path'], queryset, serializer, name)

    def _pull(self, path, queryset, serializer, key='items'):
        """
        Pull given queryset data from GoodDB
        :return:
        """
        headers = {
            'Authorization': 'Bearer %s' % self._access_token,
            'Accept': 'application/json'
        }
        self.authenticate()

        serializer = serializer()
        offset, limit = 0, 100
        count = queryset.count()
        while offset < count:
            # Get items
            items = [serializer.to_representation(instance=e) for e in queryset.all()[offset:offset + limit]]
            self._push(path, {key: items})
            offset += limit

            # Push items
            response = requests.put(f'{self._base_url}{path}', data={key: items}, headers=headers)
            try:
                response.raise_for_status()
            except requests.HTTPError:
                raise GoodDBError(response.status_code, response.content)

    def pull(self):
        """
        Pull all registered models from GoodDB
        :return:
        """
        for name, config in settings.COSINNUS_GOODDB_PULL.items():
            # Resolve model
            app_label, model_name = config['model'].rsplit('.')
            model = apps.get_model(app_label, model_name)

            # Resolve serializer
            serializer_module_name, serializer_name = config['model'].rsplit('.')
            serializer_module = import_module(serializer_module_name)
            serializer = getattr(serializer_module, serializer_name)

            # Create (public but not synced)
            queryset = model.objects.gooddb_create()
            self._push(config['path'], queryset, serializer, name)

            # Update (public, synced and modified since last run)
            queryset = model.objects.gooddb_update()
            self._push(config['path'], queryset, serializer, name)

            # Delete (not public but synced)
            queryset = model.objects.gooddb_delete()
            self._push(config['path'], queryset, serializer, name)
