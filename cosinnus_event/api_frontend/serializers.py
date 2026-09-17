from rest_framework import serializers

from cosinnus.api_frontend.serializers.tagged import CosinnusBaseTaggableObjectSerializer
from cosinnus.models import get_tag_object_model
from cosinnus_event.models import Event


class CosinnusEventPollSerializer(CosinnusBaseTaggableObjectSerializer):
    """Readonly v3 event poll serializer."""

    class Meta:
        model = Event
        fields = (
            'id',
            'title',
            'creator',
            'created',
            'group',
            'url',
        )


class CosinnusEventSerializer(CosinnusBaseTaggableObjectSerializer):
    """Readonly v3 event serializer."""

    type = serializers.SerializerMethodField()
    location = serializers.CharField(
        source='media_tag.location',
        required=False,
        allow_blank=True,
        default=None,
        help_text='On input, this string is used to determine the lat/lon fields using a nominatim service',
    )
    location_type = serializers.ChoiceField(
        source='media_tag.location_type',
        required=False,
        default=None,
        allow_blank=True,
        allow_null=True,
        choices=get_tag_object_model().LOCATION_TYPE_CHOICES,
    )
    caldav_url = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = (
            'id',
            'type',
            'title',
            'from_date',
            'to_date',
            'creator',
            'created',
            'group',
            'url',
            'location_type',
            'location',
            'image',
            'caldav_url',
        )

    def get_type(self, obj):
        state_type_map = {
            Event.STATE_SCHEDULED: 'public',
            Event.STATE_SYNCHRONIZED_EVENT: 'internal',
        }
        return state_type_map.get(obj.state)

    def get_caldav_url(self, obj):
        caldav_url = None
        user = self.context['user'] if 'user' in self.context else self.context['request'].user
        if user:
            caldav_url = obj.get_caldav_url(user)
        return caldav_url
