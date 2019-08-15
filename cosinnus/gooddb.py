import json
import logging
from datetime import datetime, timedelta

import requests
from cosinnus.api.serializers import CosinnusProjectGoodDBSerializer
from cosinnus.models.group_extra import CosinnusProject
from cosinnus_event.api.serializers import EventGoodDBSerializer
from cosinnus_event.models import Event
from django.conf import settings

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

    def push_events(self):
        """
        Pushes all public data from e. g. events and initiatives to GoodDB microservice
        :return:
        """
        queryset = Event.objects.public_upcoming()
        return self._push('/events/batch', queryset, EventGoodDBSerializer, key='events')

    def push_societies(self):
        """
        Pushes all public data from e. g. events and initiatives to GoodDB microservice
        :return:
        """
        pass

    def push_projects(self):
        """
        Pushes all public data from e. g. events and initiatives to GoodDB microservice
        :return:
        """
        queryset = CosinnusProject.objects.all_in_portal().filter(public=True)
        return self._push('/places/batch', queryset, CosinnusProjectGoodDBSerializer, key='places')

    def push_initiatives_to_good_db(self):
        raise NotImplementedError

    def _build_params(self, args_dict):
        if args_dict:
            params = ["%s=%s" % item for item in args_dict.items()]
            return u"?%s" % u'&'.join(params)
        else:
            return u""
