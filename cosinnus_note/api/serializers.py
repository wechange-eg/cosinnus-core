from django.contrib.auth import get_user_model
from rest_framework import serializers

from cosinnus.models.group_extra import CosinnusSociety
from cosinnus_note.models import Note


class NoteCreatorSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    avatar_thumbnail_url = serializers.SerializerMethodField()

    class Meta(object):
        model = get_user_model()
        fields = ('id', 'first_name', 'last_name', 'avatar_url', 'avatar_thumbnail_url')

    def get_id(self, obj):
        return obj.cosinnus_profile.get_absolute_url()

    def get_avatar_url(self, obj):
        return obj.cosinnus_profile.avatar_url

    def get_avatar_thumbnail_url(self, obj):
        return obj.cosinnus_profile.get_avatar_thumbnail_url()


class NoteGroupSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.URLField(source='get_absolute_url', read_only=True)

    class Meta(object):
        model = CosinnusSociety
        fields = ('id', 'name')


class NoteListSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.URLField(source='get_absolute_url', read_only=True)
    timestamp = serializers.DateTimeField(source='last_modified')
    creator = NoteCreatorSerializer()
    group = NoteGroupSerializer()

    class Meta(object):
        model = Note
        fields = ('id', 'title', 'text', 'video', 'timestamp',
                  'creator', 'group')


class NoteRetrieveSerializer(NoteListSerializer):
    pass
