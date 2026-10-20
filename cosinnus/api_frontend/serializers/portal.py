import logging

from rest_framework import serializers

from announcements.models import Announcement
from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.managed_tags import CosinnusManagedTag, CosinnusManagedTagType
from cosinnus.utils.html import sanitize_html

logger = logging.getLogger('cosinnus')


class CosinnusManagedTagTypeSerializer(serializers.ModelSerializer):
    """Serializer for the User Login API endpoint"""

    class Meta(object):
        model = CosinnusManagedTagType
        fields = ('id', 'name', 'prefix_label', 'color')
        read_only_fields = fields


class CosinnusManagedTagSerializer(serializers.ModelSerializer):
    """Serializer for the User Login API endpoint"""

    type = CosinnusManagedTagTypeSerializer(many=False)
    group_url = serializers.URLField(source='paired_group_url')

    class Meta(object):
        model = CosinnusManagedTag
        fields = ('slug', 'name', 'default', 'type', 'description', 'image', 'url', 'search_synonyms', 'group_url')
        read_only_fields = fields

    default = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    def get_default(self, obj):
        return bool(obj.slug == settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG)

    def get_image(self, obj):
        return f'{CosinnusPortal.get_current().get_domain()}{obj.image.url}' if obj.image else None


class CosinnusPortalErrorLogSerializer(serializers.Serializer):
    """
    Serializer for PortalErrorLogView. All entries will be shortened to a max length, but this is not enforced as
    ValidationError.
    """

    message = serializers.CharField(
        required=True,
        help_text='The message of the error that will be logged to sentry. '
        'Should not contain variables or dynamic text.',
    )
    url = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text='Optional URL (or URL fragment) of the view or place or API call where the error occured.',
    )
    stacktrace = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, help_text='Optional stacktrace, as multiline string.'
    )
    extra = serializers.DictField(
        required=False, allow_null=True, help_text='Optional extra dict field, to be filled with any additional infos.'
    )

    def validate_message(self, value):
        """Max length enforcement"""
        return value.strip()[:512]

    def validate_url(self, value):
        """Max length enforcement"""
        return value.strip()[:512]

    def validate_stacktrace(self, value):
        """Max length enforcement"""
        return value.strip()[:10240]

    def validate_extra(self, value):
        """Max length enforcement, max member count of 20 and string casting of all members"""
        ret = {}
        max_entries = 20
        if value:
            for i, (key, val) in enumerate(value.items()):
                # restrict extra to `max_entries` entries, add a print if done so
                if i >= max_entries:
                    ret['TRUNCATED'] = f'(truncated {len(value) - max_entries} more items)'
                    break
                ret[key] = str(val).strip()[:1024]
        return ret


class CosinnusPortalAnnouncementSerializer(serializers.ModelSerializer):
    """Announcement serializer."""

    level = serializers.CharField(read_only=True)
    text = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ('level', 'text', 'icon')

    def get_text(self, obj):
        text = obj.translated_text
        text = sanitize_html(text)
        return text

    def get_icon(self, obj):
        level_icon_map = {
            'success': 'fa-check',
            'info': 'fa-info-circle',
            'warning': 'fa-exclamation-circle',
            'error': 'fa-exclamation-triangle',
        }
        return level_icon_map.get(obj.level)
