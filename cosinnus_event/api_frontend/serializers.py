from cosinnus.api_frontend.serializers.tagged import CosinnusBaseTaggableObjectSerializer
from cosinnus_event.models import Event


class CosinnusEventSerializer(CosinnusBaseTaggableObjectSerializer):
    """Readonly v3 event/poll serializer."""

    class Meta:
        model = Event
        fields = (
            'id',
            'title',
            'creator',
            'created',
            'group',
            'url',
        )
