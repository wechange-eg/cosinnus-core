from cosinnus.api_frontend.serializers.tagged import CosinnusBaseTaggableObjectSerializer
from cosinnus_note.models import Note


class CosinnusNoteSerializer(CosinnusBaseTaggableObjectSerializer):
    """Readonly v3 note serializer."""

    class Meta:
        model = Note
        fields = (
            'id',
            'title',
            'text',
            'creator',
            'created',
            'group',
            'url',
        )
