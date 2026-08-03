from rest_framework import serializers

from cosinnus.api_frontend.serializers.tagged import CosinnusTaggableObjectCreatorSerializer
from cosinnus.models.idea import CosinnusIdea


class CosinnusIdeaSerializer(serializers.ModelSerializer):
    """v3 idea serializer."""

    like_count = serializers.IntegerField(read_only=True)

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
            'like_count',
        )
