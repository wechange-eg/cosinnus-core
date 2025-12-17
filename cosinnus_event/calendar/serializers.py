from rest_framework import serializers

from cosinnus.api_frontend.serializers.media_tag import CosinnusMediaTagSerializerMixin
from cosinnus.conf import settings
from cosinnus.models import BaseTagObject
from cosinnus.models.tagged import get_tag_object_model
from cosinnus.utils.permissions import get_user_token
from cosinnus_event.models import Event, EventAttendance


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


class CalendarPublicEventBBBEnabledField(serializers.BooleanField):
    """Custom field that maps the video_conference_type field to bool for BBB meetings."""

    def to_internal_value(self, data):
        bool_value = super().to_internal_value(data)
        if bool_value:
            return Event.BBB_MEETING
        return Event.NO_VIDEO_CONFERENCE

    def to_representation(self, value):
        return value == Event.BBB_MEETING


class CalendarPublicEventAttendancesListSerializer(serializers.ListSerializer):
    """A custom list serializer used to filter event attendances by going state."""

    def to_representation(self, data):
        data = data.filter(state=EventAttendance.ATTENDANCE_GOING)
        return super().to_representation(data)


class CalendarPublicEventAttendancesSerializer(serializers.ModelSerializer):
    """Readonly serializer to list the attendees of an event."""

    name = serializers.CharField(source='user.cosinnus_profile.get_full_name', read_only=True)
    avatar = serializers.URLField(source='user.cosinnus_profile.get_avatar_thumbnail_url', read_only=True)
    profile_url = serializers.URLField(source='user.cosinnus_profile.get_absolute_url', read_only=True)

    class Meta:
        model = EventAttendance
        list_serializer_class = CalendarPublicEventAttendancesListSerializer
        fields = (
            'name',
            'avatar',
            'profile_url',
        )


class CalendarPublicEventSerializer(CosinnusMediaTagSerializerMixin, serializers.ModelSerializer):
    """Complete Serializer for events in the calendar API."""

    from_date = serializers.DateTimeField(required=True)
    to_date = serializers.DateTimeField(required=True)
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
    ical_url = serializers.SerializerMethodField()

    attending = serializers.SerializerMethodField()
    attendances = CalendarPublicEventAttendancesSerializer(many=True, read_only=True)

    bbb_available = serializers.SerializerMethodField()
    bbb_restricted = serializers.SerializerMethodField()
    bbb_enabled = CalendarPublicEventBBBEnabledField(source='video_conference_type')
    bbb_url = serializers.SerializerMethodField()

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
            'ical_url',
            'attending',
            'attendances',
            'bbb_available',
            'bbb_restricted',
            'bbb_enabled',
            'bbb_url',
        )

    def create(self, validated_data):
        # get nested media tag data
        media_tag_data = validated_data.pop('media_tag', {})
        # set group and creator
        validated_data.update(
            {
                'group': self.context['group'],
                'creator': self.context['request'].user,
                'state': Event.STATE_SCHEDULED,
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
        # save media tag fields
        if media_tag_data:
            self.save_media_tag(instance.media_tag, media_tag_data)
        return instance

    def get_ical_url(self, obj):
        ical_feed_url = obj.get_feed_url()
        user = self.context['request'].user
        if user.is_authenticated and not user.is_guest:
            user_token = get_user_token(user, settings.COSINNUS_EVENT_TOKEN_EVENT_FEED)
            ical_feed_url += f'?user={user.id}&token={user_token}'
        return ical_feed_url

    def get_attending(self, obj):
        user = self.context['request'].user
        return obj.attendances.filter(user=user, state=EventAttendance.ATTENDANCE_GOING).exists()

    def get_bbb_available(self, obj):
        return settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS

    def get_bbb_restricted(self, obj):
        group = self.context['group']
        return not group.group_can_be_bbb_enabled

    def get_bbb_url(self, obj):
        bbb_room_url = None
        if settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS:
            bbb_room_url = obj.get_bbb_room_url()
        return bbb_room_url

    def validate_bbb_enabled(self, value):
        if value == Event.BBB_MEETING:
            if not settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS:
                raise serializers.ValidationError('BBB is disabled in events.')
            group = self.context['group']
            if not group.group_can_be_bbb_enabled:
                raise serializers.ValidationError('BBB creation is restricted for this group.')
        return value


class CalendarPublicEventAttendanceActionSerializer(serializers.Serializer):
    """Serializer for the post data of the attendance viewset action."""

    attending = serializers.BooleanField(required=True)
