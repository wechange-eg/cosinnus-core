from cosinnus.api_frontend.serializers.tagged import CosinnusBaseTaggableObjectSerializer
from cosinnus_note.models import Note


class CosinnusPollSerializer(CosinnusBaseTaggableObjectSerializer):
    """Readonly v3 poll serializer."""

    class Meta:
        model = Note
        fields = (
            'id',
            'title',
            'creator',
            'created',
            'group',
            'url',
        )
