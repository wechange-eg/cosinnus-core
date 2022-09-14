from datetime import datetime
import pytz
from rest_framework import serializers

from cosinnus_event.models import Event


class EventListSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.URLField(source='get_absolute_url', read_only=True)
    timestamp = serializers.DateTimeField(source='last_modified')
    image = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    location_lat = serializers.SerializerMethodField()
    location_lon = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta(object):
        model = Event
        fields = ('id', 'title', 'from_date', 'to_date', 'note', 'image',
                  'location', 'location_lat', 'location_lon', 'street', 'zipcode', 'city',
                  'timestamp', 'url', 'topics', 'tags')
    
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
    
    def get_image(self, obj):
        if not obj.attached_image:
            return None
        return self.context['request'].build_absolute_uri(obj.attached_image.static_image_url())
    
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


class EventRetrieveSerializer(EventListSerializer):
    pass
