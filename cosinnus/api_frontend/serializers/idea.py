from rest_framework import serializers

from cosinnus.api_frontend.serializers.generic import CosinnusCreatorSerializer
from cosinnus.models.idea import CosinnusIdea


class CosinnusIdeaSerializer(serializers.ModelSerializer):
    """v3 idea serializer."""

    like_count = serializers.IntegerField(read_only=True)

    creator = CosinnusCreatorSerializer(read_only=True)
    url = serializers.URLField(source='get_absolute_url', read_only=True)

    class Meta:
        model = CosinnusIdea
        fields = (
            'id',
            'title',
            'description',
            'creator',
            'created',
            'url',
            'like_count',
        )
