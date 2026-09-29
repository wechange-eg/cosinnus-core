from django.utils.timezone import now
from rest_framework import serializers

from cosinnus.api_frontend.serializers.attached_objects import CosinnusAttachedFileSerializer
from cosinnus.api_frontend.serializers.generic import CosinnusCreatorSerializer
from cosinnus.api_frontend.serializers.tagged import (
    CosinnusBaseTaggableObjectSerializer,
    CosinnusMediaTagSerializerMixin,
)
from cosinnus.conf import settings
from cosinnus.models import get_tag_object_model
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
        fields = ('id', 'text', 'created_on', 'creator')
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


class CosinnusNoteSerializer(CosinnusMediaTagSerializerMixin, CosinnusBaseTaggableObjectSerializer):
    """v3 note serializer."""

    title = serializers.CharField(required=False)
    topics = serializers.MultipleChoiceField(
        source='media_tag.get_topic_ids',
        required=False,
        allow_blank=True,
        default=list,
        choices=get_tag_object_model().TOPIC_CHOICES,
    )
    liked = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    comments = CosinnusNoteCommentSerializer(read_only=True, many=True)
    attached_images = serializers.SerializerMethodField()
    attached_file_count = serializers.SerializerMethodField()
    attached_files = serializers.SerializerMethodField()

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
            'topics',
            'like_count',
            'liked',
            'comment_count',
            'comments',
            'attached_images',
            'attached_file_count',
            'attached_files',
        )

    def get_liked(self, obj):
        user = self.context['request'].user
        return obj.is_user_liking(user)

    def get_comment_count(self, obj):
        return obj.comments.count()

    def get_attached_images(self, obj):
        attached_images = []
        for attached_object in obj.image_attachments:
            serialized_attached_object = CosinnusAttachedFileSerializer(attached_object).data
            attached_images.append(serialized_attached_object)
        return attached_images

    def get_attached_file_count(self, obj):
        return len(obj.non_image_attachments)

    def get_attached_files(self, obj):
        attached_files = []
        for attached_object in obj.non_image_attachments:
            serialized_attached_object = CosinnusAttachedFileSerializer(attached_object).data
            attached_files.append(serialized_attached_object)
        return attached_files


class CosinnusNoteForumPostSerializer(CosinnusNoteSerializer):
    def save(self, **kwargs):
        user = self.context['request'].user
        forum_group = get_cosinnus_group_model().objects.get(slug=settings.NEWW_FORUM_GROUP_SLUG)
        media_tag_data = self.validated_data.pop('media_tag', {})
        title = self.validated_data.get('title', Note.EMPTY_TITLE_PLACEHOLDER)
        instance = super().save(group=forum_group, creator=user, title=title)
        if media_tag_data:
            self.save_media_tag(instance.media_tag, media_tag_data)
        return instance


class CosinnusDeleteNoteCommentSerializer(serializers.Serializer):
    id = serializers.IntegerField()

    class Meta:
        fields = ('id',)

    def validate_id(self, value):
        if not self.instance.comments.filter(pk=value).exists():
            raise serializers.ValidationError('Comment does not exist.')
        comment = self.instance.comments.get(pk=value)
        if comment.creator != self.context['request'].user:
            raise serializers.ValidationError('User is not the creator of the comment.')
        return value

    def update(self, instance, validated_data):
        comment_id = validated_data['id']
        self.instance.comments.filter(pk=comment_id).delete()
        return instance
