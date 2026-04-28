from django.template.loader import render_to_string
from rest_framework import serializers

from cosinnus.api_frontend.serializers.conference import CosinnusConferenceSettingsSerializer
from cosinnus.conf import settings
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.urls import group_aware_reverse


class CosinnusGroupSettingsSerializer(serializers.ModelSerializer):
    """Serializer for group settings"""

    # BBB settings
    bbb_available = serializers.SerializerMethodField()
    bbb_restricted = serializers.SerializerMethodField()
    bbb_premium = serializers.SerializerMethodField()
    bbb_premium_booking_url = serializers.SerializerMethodField()

    # Events app settings
    events_ical_url = serializers.SerializerMethodField()
    events_publish_url = serializers.SerializerMethodField()
    events_event_message = serializers.SerializerMethodField()
    events_event_description_required = serializers.SerializerMethodField()
    events_reflections_enabled = serializers.SerializerMethodField()

    class Meta:
        model = get_cosinnus_group_model()
        fields = [
            'bbb_available',
            'bbb_restricted',
            'bbb_premium',
            'bbb_premium_booking_url',
            'events_ical_url',
            'events_publish_url',
            'events_event_message',
            'events_event_description_required',
            'events_reflections_enabled',
        ]

    def get_bbb_available(self, obj):
        return settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS

    def get_bbb_restricted(self, obj):
        """
        Flag indicating that BBB integration is admin restricted.
        This is the case if COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED is enabled and the groups
        enable_user_premium_choices_until is not set or in the past.
        """
        return obj.group_is_bbb_restricted

    def get_bbb_premium(self, obj):
        """
        Flag indicating that BBB premium features are available and active.
        This is the case if COSINNUS_PREMIUM_CONFERENCES_ENABLED is enabled and the group is currently or will at some
        point ever be premium due to premium blocks.
        """
        return settings.COSINNUS_PREMIUM_CONFERENCES_ENABLED and obj.is_premium_ever

    def get_bbb_premium_booking_url(self, obj):
        """Returns the premium conference booking url if enabled."""
        if settings.COSINNUS_PREMIUM_CONFERENCES_ENABLED:
            return render_to_string('cosinnus/v2/urls/conference_premium_booking_url.html')
        return ''

    def get_events_ical_url(self, obj):
        """Returns the group calendar public event ical feed."""
        if 'cosinnus_event' in obj.get_deactivated_apps():
            return ''
        return group_aware_reverse('cosinnus:team-feed', kwargs={'team_id': obj.id})

    def get_events_publish_url(self, obj):
        """Return the publish-url of the private NextCloud calendar."""
        return obj.nextcloud_calendar_publish_url

    def get_events_event_message(self, obj):
        return settings.COSINNUS_EVENT_V3_CALENDAR_EVENT_MESSAGE

    def get_events_event_description_required(self, obj):
        return settings.COSINNUS_EVENT_V3_CALENDAR_EVENT_DESCRIPTION_REQUIRED

    def get_events_reflections_enabled(self, obj):
        return 'cosinnus_event.event' in settings.COSINNUS_REFLECTABLE_OBJECTS

    def to_representation(self, instance):
        data = super().to_representation(instance)
        settings_serializer = CosinnusConferenceSettingsSerializer(parent_object=instance, group=self.instance)
        data['bbb_settings'] = settings_serializer.data
        return data
