from rest_framework import serializers

from cosinnus.api_frontend.serializers.media_tag import CosinnusMediaTagSerializerMixin
from cosinnus.models import BaseTagObject
from cosinnus.models.tagged import get_tag_object_model
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


class CalendarPublicEventSerializer(CosinnusMediaTagSerializerMixin, serializers.ModelSerializer):
    """Complete Serializer for events in the calendar API."""

    # TODO: prefetch media_tag when adding location & topics
    description = serializers.CharField(source='note')
    topics = serializers.MultipleChoiceField(
        source='media_tag.get_topic_ids',
        required=False,
        allow_blank=True,
        default=list,
        choices=get_tag_object_model().TOPIC_CHOICES,
        help_text=f'Array of ints for corresponding topics: {str(get_tag_object_model().TOPIC_CHOICES)}',
    )
    location = serializers.CharField(
        source='media_tag.location',
        required=False,
        allow_blank=True,
        default=None,
        help_text='On input, this string is used to determine the lat/lon fields using a nominatim service',
    )
    location_lat = serializers.FloatField(
        source='media_tag.location_lat',
        required=False,
        default=None,
        help_text=(
            'If not supplied, but `location` is supplied, this will be determined automatically via nominatim from the '
            'string in `location`. If supplied, will only be saved if `location` is also supplied.'
        ),
    )
    location_lon = serializers.FloatField(
        source='media_tag.location_lon',
        required=False,
        default=None,
        help_text=(
            'If not supplied, but `location` is supplied, this will be determined automatically via nominatim from the '
            'string in `location`. If supplied, will only be saved if `location` is also supplied.'
        ),
    )

    class Meta:
        model = Event
        fields = (
            'id',
            'title',
            'from_date',
            'to_date',
            'description',
            'image',
            'topics',
            'location',
            'location_lat',
            'location_lon',
        )

    def create(self, validated_data):
        # get nested media tag data
        media_tag_data = validated_data.pop('media_tag', {})
        # set group and creator
        validated_data.update(
            {
                'group': self.context['group'],
                'creator': self.context['request'].user,
            }
        )
        instance = Event.objects.create(**validated_data)
        # set event visibility to public
        instance.media_tag.visibility = BaseTagObject.VISIBILITY_ALL
        # save media tag fields
        if media_tag_data:
            self.save_media_tag(instance.media_tag, media_tag_data)
        return instance

    def update(self, instance, validated_data):
        # get nested media tag data
        media_tag_data = validated_data.pop('media_tag', {})
        # update event fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        # update media tag
        if media_tag_data:
            self.save_media_tag(instance.media_tag, media_tag_data)
        return instance
