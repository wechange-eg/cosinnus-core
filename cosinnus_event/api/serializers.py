from rest_framework import serializers

from cosinnus.api_frontend.serializers.dynamic_fields import CosinnusDynamicFieldsSerializerMixin
from cosinnus.conf import settings
from cosinnus_event.models import Event


class EventListSerializer(CosinnusDynamicFieldsSerializerMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.URLField(source='get_absolute_url', read_only=True)
    timestamp = serializers.DateTimeField(source='last_modified')
    image = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    location_lat = serializers.SerializerMethodField()
    location_lon = serializers.SerializerMethodField()
    location_type = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    group_url = serializers.SerializerMethodField()

    # dynamic field serializer parameters
    dynamic_fields_source = 'media_tag.dynamic_fields'

    class Meta(object):
        model = Event
        fields = (
            'id',
            'title',
            'from_date',
            'to_date',
            'note',
            'image',
            'location',
            'location_lat',
            'location_lon',
            'location_type',
            'street',
            'zipcode',
            'city',
            'timestamp',
            'url',
            'topics',
            'tags',
            'group_name',
            'group_url',
        )

    def get_dynamic_field_settings(self):
        if settings.COSINNUS_TAGGED_EXTRA_FIELDS and 'cosinnus_event.Event' in settings.COSINNUS_TAGGED_EXTRA_FIELDS:
            return settings.COSINNUS_TAGGED_EXTRA_FIELDS['cosinnus_event.Event']
        return {}

    def get_location(self, obj):
        location = []
        if hasattr(obj, 'media_tag') and obj.media_tag:
            location = obj.media_tag.location or None
        return location

    def get_location_lat(self, obj):
        location_lat = []
        if hasattr(obj, 'media_tag') and obj.media_tag:
            location_lat = obj.media_tag.location_lat or None
        return location_lat

    def get_location_lon(self, obj):
        location_lon = []
        if hasattr(obj, 'media_tag') and obj.media_tag:
            location_lon = obj.media_tag.location_lon or None
        return location_lon

    def get_location_type(self, obj):
        location_type = None
        if hasattr(obj, 'media_tag') and obj.media_tag:
            location_type = obj.media_tag.location_type
        return location_type

    def get_image(self, obj):
        image_url = None
        if settings.COSINNUS_EVENT_V3_CALENDAR_ENABLED and obj.image:
            image_url = obj.image.url
        elif obj.attached_image:
            image_url = obj.attached_image.static_image_url()
        if not image_url:
            return None
        return self.context['request'].build_absolute_uri(image_url)

    def get_url(self, obj):
        return obj.get_absolute_url()

    def get_topics(self, obj):
        topics = []
        if hasattr(obj, 'media_tag') and obj.media_tag:
            topics = obj.media_tag.get_topics()
        return topics

    def get_tags(self, obj):
        tags = []
        if hasattr(obj, 'media_tag') and obj.media_tag and obj.media_tag.tags:
            tags = obj.media_tag.tags.values_list('name', flat=True)
        return tags

    def get_group_name(self, obj):
        return obj.group.name

    def get_group_url(self, obj):
        return obj.group.get_absolute_url()


class EventRetrieveSerializer(EventListSerializer):
    pass
