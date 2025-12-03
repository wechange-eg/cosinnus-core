from rest_framework import serializers

from cosinnus.models import BaseTagObject
from cosinnus_event.models import Event


class CalendarPublicEventListQueryParameterSerializer(serializers.Serializer):
    """Serializer for the list API query parameters."""

    from_date = serializers.DateField(required=True, error_messages={'required': 'This parameter is required'})
    to_date = serializers.DateField(required=True, error_messages={'required': 'This parameter is required'})

    # Limit for the allowed date range between from_date and to_date to avoid db heavy requests (e.g. all events off
    # the forum group).
    MAX_DATA_RANGE_DAYS = 32

    def validate(self, data):
        # Validate maximum date range
        if (data['to_date'] - data['from_date']).days > self.MAX_DATA_RANGE_DAYS:
            raise serializers.ValidationError(f'The maximum date range is {self.MAX_DATA_RANGE_DAYS} days.')
        return data


class CalendarPublicEventListSerializer(serializers.ModelSerializer):
    """Serializer for events in the calendar list API view."""

    class Meta:
        model = Event
        fields = (
            'id',
            'title',
            'from_date',
            'to_date',
        )


class CalendarPublicEventSerializer(serializers.ModelSerializer):
    """Complete Serializer for events in the calendar API."""

    # TODO: prefetch media_tag when adding location & topics
    description = serializers.CharField(source='note')

    class Meta:
        model = Event
        fields = (
            'id',
            'title',
            'from_date',
            'to_date',
            'description',
            'image',
            #'topics',
            #'tags',
        )

    def create(self, validated_data):
        # set group and creator
        validated_data.update(
            {
                'group': self.context['group'],
                'creator': self.context['request'].user,
            }
        )
        event = super().create(validated_data)
        # set event visibility to public
        event.media_tag.visibility = BaseTagObject.VISIBILITY_ALL
        event.media_tag.save()
        return event
