from rest_framework import serializers

from cosinnus.conf import settings

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
        if len(obj.get('locations', [])) > 1:
            return obj['locations'][0].get('location', None)
        return None

    def get_mt_location_lat(self, obj):
        if len(obj.get('locations', [])) > 1:
            return obj['locations'][0].get('lat', None)
        return None

    def get_mt_location_lon(self, obj):
        if len(obj.get('locations', [])) > 1:
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
