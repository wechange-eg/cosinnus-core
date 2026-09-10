from rest_framework import serializers

from cosinnus.api_frontend.serializers.tagged import CosinnusBaseTaggableObjectSerializer
from cosinnus.conf import settings
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_note.models import Note


class CosinnusNoteSerializer(CosinnusBaseTaggableObjectSerializer):
    """Readonly v3 note serializer."""

    comment_count = serializers.SerializerMethodField()

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
            'like_count',
            'comment_count',
        )

    def get_comment_count(self, obj):
        return obj.comments.count()


class CosinnusNoteForumPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ('text',)

    def save(self, **kwargs):
        user = self.context['request'].user
        forum_group = get_cosinnus_group_model().objects.get(slug=settings.NEWW_FORUM_GROUP_SLUG)
        return super().save(group=forum_group, creator=user)
