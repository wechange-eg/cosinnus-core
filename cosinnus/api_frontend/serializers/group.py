from rest_framework import serializers

from cosinnus.conf import settings
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.urls import group_aware_reverse


class GroupSettingsSerializer(serializers.ModelSerializer):
    """Serializer for group settings"""

    # BBB settings
    bbb_available = serializers.SerializerMethodField()
    bbb_restricted = serializers.SerializerMethodField()

    # Events app settings
    events_ical_url = serializers.SerializerMethodField()

    class Meta(object):
        model = get_cosinnus_group_model()
        fields = [
            'bbb_available',
            'bbb_restricted',
            'events_ical_url',
        ]

    def get_bbb_available(self, obj):
        return settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS

    def get_bbb_restricted(self, obj):
        return obj.group_is_bbb_restricted

    def get_events_ical_url(self, obj):
        if 'cosinnus_event' in obj.get_deactivated_apps():
            return ''
        return group_aware_reverse('cosinnus:team-feed', kwargs={'team_id': obj.id})
