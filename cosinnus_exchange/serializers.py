import json
import logging

import requests
from dateutil import parser
from django.template.defaultfilters import linebreaksbr
from django.templatetags.static import static
from django.utils.html import escape, strip_tags
from rest_framework import serializers

from cosinnus.conf import settings

logger = logging.getLogger(__name__)

TOPIC_CHOICES_MAP = {v: k for k, v in settings.COSINNUS_TOPIC_CHOICES}


class ExchangeSerializerMixin(serializers.Serializer):
    external_id = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    title = serializers.CharField()
    mt_location = serializers.CharField(source='location')
    mt_location_lat = serializers.CharField(source='location_lat')
    mt_location_lon = serializers.CharField(source='location_lon')
    description = serializers.CharField()
    mt_tags = serializers.ListField(source='tags')
    mt_topics = serializers.SerializerMethodField()

    source = serializers.SerializerMethodField()
    _source = None

    def __init__(self, *args, **kwargs):
        self._source = kwargs.pop('source', None)
        super().__init__(*args, **kwargs)

    def get_source(self, obj):
        return self._source

    def get_external_id(self, obj):
        return obj.get('url') or obj.get('id')

    def get_url(self, obj):
        return obj.get('url') or obj.get('id')

    def get_mt_topics(self, obj):
        return list(filter(None, [TOPIC_CHOICES_MAP.get(t, None) for t in obj['topics']]))


class ExchangeGroupSerializer(ExchangeSerializerMixin, serializers.Serializer):
    title = serializers.CharField(source='name')
    mt_location = serializers.SerializerMethodField()
    mt_location_lat = serializers.SerializerMethodField()
    mt_location_lon = serializers.SerializerMethodField()
    icon_image_url = serializers.URLField(source='avatar')

    def get_mt_location(self, obj):
        if len(obj.get('locations', [])) > 0:
            return obj['locations'][0].get('location', None)
        return None

    def get_mt_location_lat(self, obj):
        if len(obj.get('locations', [])) > 0:
            return obj['locations'][0].get('lat', None)
        return None

    def get_mt_location_lon(self, obj):
        if len(obj.get('locations', [])) > 0:
            return obj['locations'][0].get('lon', None)
        return None


class ExchangeOrganizationSerializer(ExchangeGroupSerializer):
    pass


class ExchangeEventSerializer(ExchangeSerializerMixin, serializers.Serializer):
    from_date = serializers.CharField()
    to_date = serializers.CharField()
    description = serializers.CharField(source='note')
    icon_image_url = serializers.URLField(source='image')
    background_image_small_url = serializers.URLField(source='image')
    background_image_large_url = serializers.URLField(source='image')


class ExchangeAdhocracySerializer(ExchangeSerializerMixin, serializers.Serializer):
    """
    Serialize adhocracy+ projects into ExternalResource data.
    Example COSINNUS_EXCHANGE_BACKENDS settings:
        {
            'backend': 'cosinnus_exchange.backends.ExchangeBackend',
            'url': 'https://aplus-dev.liqd.net/api/app-projects/',
            'accept_language': 'de',
            'token_url': 'https://aplus-dev.liqd.net/api/token/',
            'username': env('WECHANGE_EXCHANGE_ADHOCRACY_USER'),
            'password': env('WECHANGE_EXCHANGE_ADHOCRACY_PASSWORD'),
            'source': 'adhocracy+',
            'model': 'cosinnus_exchange.ExchangeExternalResource',
            'serializer': 'cosinnus_exchange.serializers.ExchangeAdhocracySerializer',
            'serializer_kwargs': {
                'base_url': 'https://aplus-dev.liqd.net'
            },
        },
    """

    title = serializers.CharField(source='name')
    mt_location = serializers.SerializerMethodField()
    mt_location_lat = serializers.SerializerMethodField()
    mt_location_lon = serializers.SerializerMethodField()
    mt_tags = serializers.SerializerMethodField()
    icon_image_url = serializers.URLField(source='organisation_logo')
    background_image_small_url = serializers.URLField(source='image')
    background_image_large_url = serializers.URLField(source='image')
    description_detail = serializers.SerializerMethodField()
    contact_info = serializers.SerializerMethodField()
    website_url = serializers.URLField(source='contact_url')
    base_url = None

    def __init__(self, *args, **kwargs):
        self.base_url = kwargs.pop('base_url', None)
        super().__init__(*args, **kwargs)

    def get_external_id(self, obj):
        return self.get_url(obj)

    def get_url(self, obj):
        return self.base_url + obj.get('url')

    def get_mt_location(self, obj):
        return None

    def _get_location_coordinates(self, obj):
        """
        Parsing GeoJSON "point" value, handling string and JSON. Example:
        "{'type': 'Feature', 'properties': {}, 'geometry': {'type': 'Point', 'coordinates': [9.997559, 54.249822]}}"
        """
        coordinates = None
        if obj.get('point'):
            try:
                point = obj.get('point')
                if isinstance(point, str):
                    point = point.replace("'", '"')
                    point = json.loads(point)
                coordinates = point.get('geometry', {}).get('coordinates', None)
            except Exception as e:
                logger.error(
                    'ExchangeAdhocracySerializer: Could not parse location coordinates.', extra={'exception': e}
                )
        return coordinates

    def get_mt_location_lat(self, obj):
        lat = None
        coordinates = self._get_location_coordinates(obj)
        if coordinates and len(coordinates) == 2:
            lat = coordinates[1]
        return lat

    def get_mt_location_lon(self, obj):
        lon = None
        coordinates = self._get_location_coordinates(obj)
        if coordinates and len(coordinates) == 2:
            lon = coordinates[0]
        return lon

    def get_mt_tags(self, obj):
        return []

    def get_mt_topics(self, obj):
        return []

    def get_description_detail(self, obj):
        description_detail = ''
        organisation = obj.get('organisation')
        if organisation:
            description_detail += f'<p><strong>Organisation:</strong> {organisation}</p>'
        participation_time_start = obj.get('dateStart')
        participation_time_end = obj.get('dateEnd')
        if participation_time_start and participation_time_end:
            description_detail += (
                f'<p><strong>Beteiligungsphase:</strong> {participation_time_start} - {participation_time_end}</p>'
            )
        description = obj.get('description')
        if description:
            description_detail += f'<p>{description}</p>'
        url = self.get_url(obj)
        if url:
            description_detail += f'<p><a href="{url}" target="_blank">Mehr erfahren und beteiligen</a></p>'
        return description_detail

    def get_contact_info(self, obj):
        contact = None
        if obj.get('has_contact_info', False):
            contact_fields = ['contact_name', 'contact_address_text', 'contact_phone', 'contact_email']
            contact = ''
            for contact_field in contact_fields:
                contact_field_value = obj.get(contact_field)
                if contact_field_value:
                    if contact:
                        contact += '<br>'
                    contact += linebreaksbr(escape(contact_field_value))
        return contact


class ExchangeDipasSerializer(ExchangeSerializerMixin, serializers.Serializer):
    """
    Serialize DIPAS projects into ExternalResource data.
    Multiple APIs are used for the data:
    - Project list with most data: https://dialog-kiel.de/drupal/dipas-pds/projects
    - Project list with location points: https://dialog-kiel.de/drupal/dipas/navigator/cockpitdatamap
    - Project detail with image url and contact: https://<project-url>/drupal/dipas/init
    - Project detail with html description: https://<project-url>/drupal/dipas/projectinfo

    Example COSINNUS_EXCHANGE_BACKENDS settings:
     {
        'backend': 'cosinnus_exchange.backends.ExchangeBackend',
        'url': 'https://dialog-kiel.de/drupal/dipas-pds/projects',
        'result_key': 'features',
        'source': 'DIPAS',
        'model': 'cosinnus_exchange.ExchangeExternalResource',
        'serializer': 'cosinnus_exchange.serializers.ExchangeDipasSerializer',
        'serializer_kwargs': {
             'location_api_url': 'https://dialog-kiel.de/drupal/dipas/navigator/cockpitdatamap',
        },
    }
    """

    title = serializers.SerializerMethodField()
    mt_location = serializers.SerializerMethodField()
    mt_location_lat = serializers.SerializerMethodField()
    mt_location_lon = serializers.SerializerMethodField()
    mt_tags = serializers.SerializerMethodField()
    icon_image_url = serializers.SerializerMethodField()
    background_image_small_url = serializers.SerializerMethodField()
    background_image_large_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    description_detail = serializers.SerializerMethodField()
    contact_info = serializers.SerializerMethodField()
    website_url = serializers.SerializerMethodField()

    # API url with location data
    location_api_url = None
    # API path for project details containing location and organization info
    DETAIL_API_PATH = '/drupal/dipas/init'
    # API path for project details containing the formatted HTML description
    DESCRIPTION_API_PATH = '/drupal/dipas/projectinfo'

    # Storage for additional API data
    location_api_data = None
    images = None
    descriptions = None

    def __init__(self, *args, **kwargs):
        self.location_api_url = kwargs.pop('location_api_url')
        super().__init__(*args, **kwargs)
        self.detail_data = {}
        self.descriptions = {}

    def _get_project_base_url(self, obj):
        """Returns the base project URL for the additional APIs."""
        project_url = self.get_url(obj)
        if project_url.endswith('/#'):
            project_url = project_url[:-2]
        return project_url

    def get_external_id(self, obj):
        return self.get_url(obj)

    def get_url(self, obj):
        return obj.get('properties', {}).get('website')

    def get_title(self, obj):
        return obj.get('properties', {}).get('nameFull')

    def get_mt_location(self, obj):
        return None

    def _get_location_data(self, project_id):
        """Get the location data for the project from the additional location API."""
        if not self.location_api_data:
            try:
                response = requests.get(self.location_api_url)
                response.raise_for_status()
                self.location_api_data = json.loads(response.content)
            except Exception as e:
                logger.warning('ExchangeDipasSerializer: Could not get location data.', extra={'exception': e})

        project_location_data = None
        if self.location_api_data:
            for location_data in self.location_api_data.get('features', []):
                if location_data.get('properties', {}).get('id') == project_id:
                    project_location_data = location_data
                    break
        return project_location_data

    def _get_location_coordinates(self, obj):
        """Get the location coordinates from the location API data."""
        coordinates = None
        project_id = obj.get('properties', {}).get('id')
        if project_id:
            location_data = self._get_location_data(project_id)
            if location_data:
                coordinates = location_data.get('geometry', {}).get('coordinates')
        return coordinates

    def get_mt_location_lat(self, obj):
        lat = None
        coordinates = self._get_location_coordinates(obj)
        if coordinates and len(coordinates) == 2:
            lat = coordinates[1]
        return lat

    def get_mt_location_lon(self, obj):
        lon = None
        coordinates = self._get_location_coordinates(obj)
        if coordinates and len(coordinates) == 2:
            lon = coordinates[0]
        return lon

    def get_mt_tags(self, obj):
        return []

    def get_mt_topics(self, obj):
        return []

    def get_icon_image_url(self, obj):
        """Use static DIPAS logo, as the APIs do not provide a square logo."""
        return static('images/dipas-logo.png')

    def _get_project_detail_data(self, obj):
        """Get the project detail data from the additional detail API."""
        project_url = self._get_project_base_url(obj)
        if project_url not in self.detail_data:
            detail_api_url = project_url + self.DETAIL_API_PATH
            try:
                response = requests.get(detail_api_url)
                response.raise_for_status()
                detail_data = json.loads(response.content)
                self.detail_data[project_url] = detail_data
            except Exception as e:
                logger.warning('ExchangeDipasSerializer: Could not get project details.', extra={'exception': e})
        return self.detail_data.get(project_url, {})

    def _get_image_url(self, obj):
        """Get the image from the project detail data."""
        image_url = ''
        project_details = self._get_project_detail_data(obj)
        if project_details:
            image_url = project_details.get('landingpage', {}).get('image', {}).get('path', '')
            if image_url and image_url.startswith('//'):
                image_url = 'https:' + image_url
        return image_url

    def get_background_image_small_url(self, obj):
        return self._get_image_url(obj)

    def get_background_image_large_url(self, obj):
        return self._get_image_url(obj)

    def get_description(self, obj):
        """Get description as text"""
        return strip_tags(obj.get('properties', {}).get('description')).replace('&nbsp;', ' ')

    def _get_description_html(self, obj):
        """Get the html description from the additional description API."""
        project_url = self._get_project_base_url(obj)
        if project_url not in self.descriptions:
            description_api_url = project_url + self.DESCRIPTION_API_PATH
            description_data = None
            try:
                response = requests.get(description_api_url)
                response.raise_for_status()
                description_data = json.loads(response.content)
            except Exception as e:
                logger.warning('ExchangeDipasSerializer: Could not get project description.', extra={'exception': e})
            if description_data:
                for paragraph_data in description_data.get('content', []):
                    if (
                        paragraph_data.get('type') == 'paragraph'
                        and paragraph_data.get('bundle') == 'text'
                        and paragraph_data.get('field_text')
                    ):
                        description = paragraph_data.get('field_text')
                        self.descriptions[project_url] = description
                        break
            else:
                # Fallback to the unformatted description in the main API.
                description = obj.get('properties', {}).get('description', '').replace('&nbsp;', ' ')
                self.descriptions[project_url] = description
        return self.descriptions.get(project_url, '')

    def get_description_detail(self, obj):
        description_detail = ''
        organisation = obj.get('properties', {}).get('owner')
        if organisation:
            description_detail += f'<p><strong>Organisation:</strong> {organisation}</p>'
        participation_start = obj.get('properties', {}).get('dateStart')
        participation_end = obj.get('properties', {}).get('dateEnd')
        if participation_start and participation_end:
            start_date = parser.parse(participation_start).strftime('%d.%m.%y')
            end_date = parser.parse(participation_end).strftime('%d.%m.%y')
            description_detail += f'<p><strong>Beteiligungsphase:</strong> vom {start_date} bis {end_date}</p>'
        description = self._get_description_html(obj)
        if description:
            description_detail += f'<p>{description}</p>'
        url = self.get_url(obj)
        if url:
            description_detail += f'<p><a href="{url}" target="_blank">Mehr erfahren und beteiligen</a></p>'
        return description_detail

    def get_contact_info(self, obj):
        """Get the contact info from the project detail data."""
        contact = ''
        project_details = self._get_project_detail_data(obj)
        if project_details and project_details.get('projectowner'):
            fields = ['name', 'street1', 'street2', 'zip', 'city', 'telephone', 'email']
            no_linebreak_after_fields = ['zip']
            for field in fields:
                field_value = project_details.get('projectowner').get(field)
                if field_value:
                    contact += field_value
                    contact += '<br/>' if field not in no_linebreak_after_fields else ' '
        return contact

    def get_website_url(self, obj):
        website_url = ''
        project_details = self._get_project_detail_data(obj)
        if project_details and project_details.get('projectowner'):
            website_url = project_details.get('projectowner').get('website')
        return website_url
