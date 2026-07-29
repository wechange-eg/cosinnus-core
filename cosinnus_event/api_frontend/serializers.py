from cosinnus.api_frontend.serializers.tagged import CosinnusBaseTaggableObjectSerializer
from cosinnus_event.models import Event


class CosinnusEventPollSerializer(CosinnusBaseTaggableObjectSerializer):
    """Readonly v3 event poll serializer."""

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


class CosinnusEventSerializer(CosinnusBaseTaggableObjectSerializer):
    """Readonly v3 event serializer."""

    class Meta:
        model = Event
        fields = (
            'id',
            'title',
            'from_date',
            'to_date',
            'creator',
            'created',
            'group',
            'url',
        )
