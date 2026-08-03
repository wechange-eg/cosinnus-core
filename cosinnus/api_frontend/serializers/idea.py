from rest_framework import serializers

from cosinnus.api_frontend.serializers.tagged import CosinnusTaggableObjectCreatorSerializer
from cosinnus.models.idea import CosinnusIdea


class CosinnusIdeaSerializer(serializers.ModelSerializer):
    """v3 idea serializer."""

    likes_count = serializers.IntegerField(source='like_count', read_only=True)

    creator = CosinnusTaggableObjectCreatorSerializer(read_only=True)
    url = serializers.URLField(source='get_absolute_url', read_only=True)

    class Meta:
        model = CosinnusIdea
        fields = (
            'id',
            'title',
            'creator',
            'created',
            'url',
            'likes_count',
        )
