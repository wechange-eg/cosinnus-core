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

    class Meta:
        model = Event
        fields = (
            'id',
            'title',
            'from_date',
            'to_date',
            'creator',
            'created',
            'group',
            'url',
            'location_type',
            'location',
        )
