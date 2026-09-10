from django.utils.timezone import now
from rest_framework import serializers

from cosinnus.api_frontend.serializers.generic import CosinnusCreatorSerializer
from cosinnus.api_frontend.serializers.tagged import CosinnusBaseTaggableObjectSerializer
from cosinnus.conf import settings
from cosinnus.templatetags.cosinnus_tags import filter_comments_for_user
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_note.models import Comment, Note


class CosinnusNoteCommentListSerializer(serializers.ListSerializer):
    """A custom list serializer used to filter comments for a user."""

    def to_representation(self, data):
        user = self.context['request'].user
        data = filter_comments_for_user(data, user)
        return super().to_representation(data)


class CosinnusNoteCommentSerializer(serializers.ModelSerializer):
    creator = CosinnusCreatorSerializer(read_only=True)
    created_on = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Comment
        fields = ('text', 'created_on', 'creator')
        list_serializer_class = CosinnusNoteCommentListSerializer

    def update(self, instance, validated_data):
        user = self.context['request'].user
        Comment.objects.create(
            creator=user,
            note=instance,
            text=validated_data['text'],
        )
        instance.update_last_action(now(), user, save=True)
        return instance


class CosinnusNoteSerializer(CosinnusBaseTaggableObjectSerializer):
    """Readonly v3 note serializer."""

    comment_count = serializers.SerializerMethodField()
    comments = CosinnusNoteCommentSerializer(read_only=True, many=True)

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
            'comments',
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
