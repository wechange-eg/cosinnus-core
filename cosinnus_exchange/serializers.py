import json
import logging

from django.template.defaultfilters import linebreaksbr
from django.utils.html import escape
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
        participation_time_display = obj.get('participation_time_display')
        if participation_time_display:
            description_detail += f'<p><strong>Beteiligungsphase:</strong> {participation_time_display}</p>'
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
