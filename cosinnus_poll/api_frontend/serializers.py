from cosinnus.api_frontend.serializers.tagged import CosinnusBaseTaggableObjectSerializer
from cosinnus_poll.models import Poll


class CosinnusPollSerializer(CosinnusBaseTaggableObjectSerializer):
    """Readonly v3 poll serializer."""

    class Meta:
        model = Poll
        fields = (
            'id',
            'title',
            'creator',
            'created',
            'group',
            'url',
        )
