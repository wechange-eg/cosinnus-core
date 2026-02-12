from rest_framework import serializers

from cosinnus.conf import settings
from cosinnus.utils.group import get_cosinnus_group_model


class GroupSettingsSerializer(serializers.ModelSerializer):
    """Serializer for group settings"""

    bbb_available = serializers.SerializerMethodField()
    bbb_restricted = serializers.SerializerMethodField()
    bbb_enabled = serializers.SerializerMethodField()

    class Meta(object):
        model = get_cosinnus_group_model()
        fields = [
            'bbb_available',
            'bbb_restricted',
            'bbb_enabled',
        ]

    def get_bbb_available(self, obj):
        return settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS

    def get_bbb_restricted(self, obj):
        return obj.group_is_bbb_restricted

    def get_bbb_enabled(self, obj):
        return obj.group_is_bbb_enabled
