from django.contrib.auth import get_user_model
from rest_framework import serializers

from cosinnus.utils.permissions import check_user_can_see_user


class CosinnusCreatorSerializer(serializers.ModelSerializer):
    """
    Readonly serializer for an object creator.
    Checks user visibility before display.
    """

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

    def to_representation(self, instance):
        """Check view permissions for creator."""
        user = None
        if 'user' in self.context:
            user = self.context['user']
        if 'request' in self.context:
            user = self.context['request'].user
        if not user or not check_user_can_see_user(user, instance):
            return None
        return super().to_representation(instance)
