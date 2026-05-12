from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.functional import cached_property
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from cosinnus.api_frontend.serializers.attached_objects import CosinnusAttachedFileSerializer
from cosinnus.api_frontend.serializers.conference import CosinnusConferenceSettingsSerializer
from cosinnus.api_frontend.serializers.dynamic_fields import CosinnusDynamicFieldsSerializerMixin
from cosinnus.api_frontend.serializers.tagged import CosinnusMediaTagSerializerMixin
from cosinnus.conf import settings
from cosinnus.models.group import CosinnusBaseGroup
from cosinnus.models.tagged import BaseTaggableObjectReflection, BaseTagObject, get_tag_object_model
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.permissions import check_object_write_access
from cosinnus_event.models import Event, EventAttendance


class CosinnusCalendarListQueryParameterSerializer(serializers.Serializer):
    """Serializer for the list API query parameters."""

    from_date = serializers.DateField(required=True, error_messages={'required': 'This parameter is required'})
    to_date = serializers.DateField(required=True, error_messages={'required': 'This parameter is required'})

    # Limit for the allowed date range between from_date and to_date to avoid db heavy requests (e.g. all events off
    # the forum group).
    MAX_DATA_RANGE_DAYS = 42

    def validate(self, data):
        # Validate maximum date range
        if (data['to_date'] - data['from_date']).days > self.MAX_DATA_RANGE_DAYS:
            raise serializers.ValidationError(f'The maximum date range is {self.MAX_DATA_RANGE_DAYS} days.')
        return data


class CosinnusCalendarListSerializer(serializers.ModelSerializer):
    """Serializer for events in the calendar list API view."""

    attending = serializers.SerializerMethodField()
    group = serializers.IntegerField(source='group.id', read_only=True)

    class Meta:
        model = Event
        fields = (
            'id',
            'group',
            'title',
            'from_date',
            'to_date',
            'attending',
        )

    def get_attending(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        return obj.attendances.filter(user=user, state=EventAttendance.ATTENDANCE_GOING).exists()


class CalendarPublicEventAttendancesListSerializer(serializers.ListSerializer):
    """A custom list serializer used to filter event attendances by going state."""

    def to_representation(self, data):
        data = data.filter(state=EventAttendance.ATTENDANCE_GOING)
        return super().to_representation(data)


class CosinnusCalendarEventAttendancesSerializer(serializers.ModelSerializer):
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


class CosinnusCalendarEventCreatorSerializer(serializers.ModelSerializer):
    """Readonly serializer for the creator of an event."""

    name = serializers.CharField(source='cosinnus_profile.get_full_name', read_only=True)
    avatar = serializers.URLField(source='cosinnus_profile.get_avatar_thumbnail_url', read_only=True)
    profile_url = serializers.URLField(source='cosinnus_profile.get_absolute_url', read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            'name',
            'avatar',
            'profile_url',
        )


class BBBRoomUrlsMixin:
    """A helper mixing to compute the BBB room url method field values used in multiple APIs."""

    def get_bbb_url(self, obj):
        user = self.context['request'].user
        bbb_room_url = None
        if user.is_authenticated and settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS and obj.can_have_bbb_room():
            if obj.media_tag.bbb_room:
                bbb_room_url = obj.media_tag.bbb_room.get_absolute_url()
            else:
                obj.check_and_create_bbb_room(threaded=True)
        return bbb_room_url

    def get_bbb_guest_url(self, obj):
        bbb_room_guest_url = None
        if (
            settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS
            and obj.can_have_bbb_room()
            and obj.media_tag.bbb_room
            and obj.media_tag.show_bbb_guest_access_outside_of_conference
        ):
            guest_token = obj.media_tag.bbb_room.get_guest_token()
            bbb_room_guest_url = reverse('cosinnus:bbb-room-guest-access', kwargs={'guest_token': guest_token})
        return bbb_room_guest_url


class CosinnusCalendarEventSerializer(
    CosinnusDynamicFieldsSerializerMixin,
    CosinnusMediaTagSerializerMixin,
    BBBRoomUrlsMixin,
    CosinnusCalendarListSerializer,
):
    """Complete Serializer for events in the calendar API."""

    from_date = serializers.DateTimeField(required=True)
    to_date = serializers.DateTimeField(required=True)
    description = serializers.CharField(
        source='note',
        required=settings.COSINNUS_EVENT_V3_CALENDAR_EVENT_DESCRIPTION_REQUIRED,
        allow_null=False if settings.COSINNUS_EVENT_V3_CALENDAR_EVENT_DESCRIPTION_REQUIRED else True,
        allow_blank=False if settings.COSINNUS_EVENT_V3_CALENDAR_EVENT_DESCRIPTION_REQUIRED else True,
    )
    creator = CosinnusCalendarEventCreatorSerializer(read_only=True)
    can_edit = serializers.SerializerMethodField()
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
    location_type = serializers.ChoiceField(
        source='media_tag.location_type',
        required=False,
        default=None,
        allow_blank=True,
        allow_null=True,
        choices=get_tag_object_model().LOCATION_TYPE_CHOICES,
    )
    bbb_url = serializers.SerializerMethodField()
    bbb_guest_url = serializers.SerializerMethodField()
    external_video_conference_url = serializers.URLField(
        source='media_tag.external_video_conference_url',
        required=False,
        default=None,
        allow_blank=True,
        allow_null=True,
    )

    ical_url = serializers.SerializerMethodField()

    attendances = CosinnusCalendarEventAttendancesSerializer(many=True, read_only=True)
    bookmarked = serializers.SerializerMethodField()

    image = Base64ImageField(required=False, default=None, allow_null=True)
    attached_files = serializers.SerializerMethodField()

    # dynamic field serializer parameters
    dynamic_fields_source = 'media_tag.dynamic_fields'

    class Meta:
        model = Event
        fields = (
            'id',
            'title',
            'from_date',
            'to_date',
            'description',
            'creator',
            'can_edit',
            'topics',
            'location',
            'location_lat',
            'location_lon',
            'location_type',
            'bbb_url',
            'bbb_guest_url',
            'external_video_conference_url',
            'ical_url',
            'attending',
            'attendances',
            'bookmarked',
            'image',
            'attached_files',
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # appy field level permissions
        user = self.context['request'].user
        if not check_object_write_access(instance, user):
            data['attendances'] = []
        return data

    def create_or_update(self, validated_data, instance=None):
        # copy validate_data for dynamic field serializer
        complete_validated_data = validated_data.copy()
        # get nested media tag data
        media_tag_data = validated_data.pop('media_tag', {})
        if not instance:
            # create event
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
            instance.media_tag.save()
        else:
            # update event
            for field, value in validated_data.items():
                setattr(instance, field, value)
            instance.save()
        # save media tag fields
        if media_tag_data:
            self.save_media_tag(instance.media_tag, media_tag_data)
        # save dynamic fields data
        self.save_dynamic_fields(complete_validated_data, instance.media_tag)
        return instance

    def create(self, validated_data):
        return self.create_or_update(validated_data)

    def update(self, instance, validated_data):
        return self.create_or_update(validated_data, instance=instance)

    def get_can_edit(self, obj):
        return check_object_write_access(obj, self.context['request'].user)

    def get_ical_url(self, obj):
        return obj.get_feed_url()

    def get_bookmarked(self, obj):
        user = self.context['request'].user
        return obj.is_user_starring(user)

    def get_attached_files(self, obj):
        attached_files = []
        for attached_object in obj.file_attachments:
            serialized_attached_object = CosinnusAttachedFileSerializer(attached_object).data
            attached_files.append(serialized_attached_object)
        return attached_files

    def get_model(self):
        return Event

    def get_dynamic_field_settings(self):
        if settings.COSINNUS_TAGGED_EXTRA_FIELDS and 'cosinnus_event.Event' in settings.COSINNUS_TAGGED_EXTRA_FIELDS:
            return settings.COSINNUS_TAGGED_EXTRA_FIELDS['cosinnus_event.Event']
        return {}


class CosinnusCalendarEventAttendanceSerializer(serializers.Serializer):
    """Serializer for the post data of the attendance viewset action."""

    attending = serializers.BooleanField(required=True)

    def to_representation(self, instance):
        user = self.context['request'].user
        attending = (
            instance.attendances.filter(user=user, state=EventAttendance.ATTENDANCE_GOING).exists()
            if user.is_authenticated
            else False
        )
        return {
            'attending': attending,
        }

    def update(self, instance, validated_data):
        user = self.context['request'].user
        attending = validated_data['attending']
        user_attendance = instance.attendances.filter(user=user).first()
        if attending:
            # user is attending
            if user_attendance:
                if user_attendance.state != EventAttendance.ATTENDANCE_GOING:
                    # set state to "going" of existing event attendance
                    user_attendance.state = EventAttendance.ATTENDANCE_GOING
                    user_attendance.save()
            else:
                # no event attendance exists, create a new one
                instance.attendances.create(user=user, state=EventAttendance.ATTENDANCE_GOING)
        elif user_attendance and user_attendance.state != EventAttendance.ATTENDANCE_NOT_GOING:
            # user not attending, but event attendance exists, set state to "not going"
            user_attendance.state = EventAttendance.ATTENDANCE_NOT_GOING
            user_attendance.save()
        return instance


class CalendarPublicEventBBBEnabledField(serializers.BooleanField):
    """Custom field that maps the video_conference_type field to bool for BBB meetings."""

    def to_internal_value(self, data):
        bool_value = super().to_internal_value(data)
        if bool_value:
            return Event.BBB_MEETING
        return Event.NO_VIDEO_CONFERENCE

    def to_representation(self, value):
        return value == Event.BBB_MEETING


class CosinnusCalendarEventBBBRoomSerializer(BBBRoomUrlsMixin, serializers.ModelSerializer):
    """Serializer for event BBB room and conference settings."""

    enabled = CalendarPublicEventBBBEnabledField(source='video_conference_type')
    bbb_url = serializers.SerializerMethodField()
    bbb_guest_url = serializers.SerializerMethodField()

    # settings serialization is done manually in to_representation and to_internal_value
    settings = None

    class Meta:
        model = Event
        fields = (
            'enabled',
            'bbb_url',
            'bbb_guest_url',
        )

    def validate_enabled(self, value):
        if value == Event.BBB_MEETING:
            if not settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS:
                raise serializers.ValidationError('BBB is disabled in events.')
            group = self.context['group']
            if not group.group_can_be_bbb_enabled:
                raise serializers.ValidationError('BBB creation is restricted for this group.')
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        settings_serializer = CosinnusConferenceSettingsSerializer(parent_object=instance, group=self.instance.group)
        data['settings'] = settings_serializer.data
        return data

    def to_internal_value(self, data):
        settings_data = data.pop('settings', None)
        if settings_data:
            settings_serializer = CosinnusConferenceSettingsSerializer(
                data=settings_data, parent_object=self.instance, group=self.instance.group
            )
            settings_serializer.is_valid(raise_exception=True)
            settings_serializer.save()
        return super().to_internal_value(data)


class CosinnusCalendarBBBRoomUrlsSerializer(BBBRoomUrlsMixin, serializers.ModelSerializer):
    """Serializer for BBB room urls, that is used by an API periodically pulled during BBB room creation."""

    bbb_url = serializers.SerializerMethodField()
    bbb_guest_url = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = (
            'bbb_url',
            'bbb_guest_url',
        )


class CosinnusCalendarGroupReflectionSerializer(serializers.Serializer):
    """
    Serializer for event group reflections used for validation.
    Contains group info and flag if the event is reflected.
    """

    id = serializers.IntegerField()
    name = serializers.CharField(required=False)
    avatar = serializers.CharField(required=False)
    reflected = serializers.BooleanField()

    # contains user groups used for group id validation
    user_group = None

    def __init__(self, instance=None, group=None, reflected=None, user_groups=None, **kwargs):
        self.user_groups = user_groups
        super().__init__(instance, **kwargs)
        if group and reflected is not None:
            # initialize fields for GETs, for POSTs the required fields are automatically initialized from the POST data
            self.fields['id'].initial = group.id
            self.fields['name'].initial = group.name
            self.fields['avatar'].initial = group.get_avatar_thumbnail_url()
            self.fields['reflected'].initial = reflected

    def validate_id(self, value):
        """Check if the group id is a user group and reflections are allowed."""
        if not any(user_group.pk == value for user_group in self.user_groups):
            raise serializers.ValidationError('Invalid user group.')
        return value


class CosinnusCalendarEventReflectSerializer(serializers.Serializer):
    """Serializer for event reflections.
    Contains a list of all user groups with a writable flag, indicating if the event is reflected in the group.
    Note: The reflection logic for the calendar events is different from the original v2 logic
          (see group_assign_reflected_object). Here we allow reflections of an event into any user group.
    """

    spaces = serializers.JSONField()

    @cached_property
    def reflection_user_groups(self):
        """Helper to get user groups and projects excluding the event group."""
        user = self.context['request'].user
        group = self.context['group']
        user_groups = get_cosinnus_group_model().objects.get_for_user(user)
        user_groups = [
            user_group
            for user_group in user_groups
            if user_group.pk != group.pk
            and user_group.type in [CosinnusBaseGroup.TYPE_PROJECT, CosinnusBaseGroup.TYPE_SOCIETY]
        ]
        return user_groups

    @property
    def event_reflection_groups(self):
        """Helper to get the groups where the event is reflected."""
        return BaseTaggableObjectReflection.get_group_ids_for_object(self.instance)

    def to_representation(self, instance):
        group_reflections = []
        for user_group in self.reflection_user_groups:
            reflected_in_group = user_group.pk in self.event_reflection_groups
            group_reflection_serializer = CosinnusCalendarGroupReflectionSerializer(
                group=user_group, reflected=reflected_in_group
            )
            group_reflections.append(group_reflection_serializer.data)
        data = {'spaces': group_reflections}
        return data

    def validate(self, data):
        """Validate data using the CalendarPublicEventGroupReflectionSerializer serializer."""
        group_reflections_data = data.get('spaces')
        for group_reflection_data in group_reflections_data:
            group_reflection_serializer = CosinnusCalendarGroupReflectionSerializer(
                user_groups=self.reflection_user_groups, data=group_reflection_data, context=self.context
            )
            group_reflection_serializer.is_valid(raise_exception=True)
        return data

    def update(self, instance, validated_data):
        """Save reflection changes."""
        event_reflection_groups = self.event_reflection_groups
        for group_reflection_data in validated_data['spaces']:
            reflection_group_id = group_reflection_data['id']
            reflected = group_reflection_data['reflected']
            event_content_type = ContentType.objects.get_for_model(Event)
            if reflected and reflection_group_id not in event_reflection_groups:
                # create event reflection
                BaseTaggableObjectReflection.objects.create(
                    content_type=event_content_type,
                    object_id=self.instance.id,
                    group_id=reflection_group_id,
                    creator=self.context['request'].user,
                )
            elif not reflected and reflection_group_id in event_reflection_groups:
                # delete existing event reflection
                BaseTaggableObjectReflection.objects.get(
                    content_type=event_content_type, object_id=self.instance.id, group_id=reflection_group_id
                ).delete()
        return instance
