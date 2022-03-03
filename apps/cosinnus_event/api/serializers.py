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
    url = serializers.SerializerMethodField()

    class Meta(object):
        model = Event
        fields = ('id', 'title', 'from_date', 'to_date', 'note', 'image',
                  'location', 'location_lat', 'location_lon', 'street', 'zipcode', 'city',
                  'timestamp', 'url', 'topics', 'tags')

    def get_image(self, obj):
        if not obj.attached_image:
            return None
        return self.context['request'].build_absolute_uri(obj.attached_image.static_image_url())
    
    def get_url(self, obj):
        return obj.get_absolute_url()

    def get_topics(self, obj):
        return obj.media_tag.get_topics()

    def get_tags(self, obj):
        return obj.media_tag.tags.values_list('name', flat=True)


class EventRetrieveSerializer(EventListSerializer):
    pass
