from django.contrib.auth import get_user_model
from rest_framework import serializers

from cosinnus.models import BaseTagObject
from cosinnus.templatetags.cosinnus_tags import textfield_with_html


class CosinnusCreatorSerializer(serializers.ModelSerializer):
    """
    Readonly serializer for an object creator.
    Checks user visibility before display.
    """

    name = serializers.CharField(source='cosinnus_profile.get_full_name', read_only=True)
    avatar = serializers.URLField(source='cosinnus_profile.get_avatar_thumbnail_url', read_only=True)
    profile_url = serializers.URLField(source='cosinnus_profile.get_absolute_url', read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            'name',
            'avatar',
            'profile_url',
            'is_mine',
        )

    def get_is_mine(self, obj):
        user = self.context['request'].user
        return user and obj.pk == user.pk

    def to_representation(self, instance):
        """Check view permissions for creator."""
        user = self.context['request'].user
        if not user or (
            not user.is_authenticated and instance.cosinnus_profile.media_tag.visibility != BaseTagObject.VISIBILITY_ALL
        ):
            # creator is hidden for unauthenticated users unless the visibility is set to all.
            return None
        return super().to_representation(instance)


class CosinnusButtonSerializer(serializers.Serializer):
    """Generic button serializer"""

    label = serializers.CharField()
    url = serializers.URLField()


class CosinnusPopupSerializer(serializers.Serializer):
    """Generic user popup serializer."""

    id = serializers.CharField()
    header = serializers.CharField()
    text = serializers.CharField()
    primary_button = CosinnusButtonSerializer(required=False)
    secondary_button = CosinnusButtonSerializer(required=False)
    close_button_label = serializers.CharField(required=False, allow_null=True)
    close_url = serializers.URLField(required=False)
    show_on_url_patterns = serializers.ListField(required=False, child=serializers.CharField())

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # render Markdown or sanitize HTML
        ret['text'] = textfield_with_html(ret['text'])
        return ret
