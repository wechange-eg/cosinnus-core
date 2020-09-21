# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from django.contrib.auth import get_user_model
from rest_framework import serializers

from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.models.group import CosinnusGroup
from django.templatetags.static import static


__all__ = ('ConferenceSerializer', )

from cosinnus.utils.files import image_thumbnail_url

from cosinnus.utils.permissions import check_ug_admin, check_user_superuser
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_event.models import ConferenceEvent


class ConferenceRoomSerializer(serializers.ModelSerializer):
    TYPE_MAP = {
        CosinnusConferenceRoom.TYPE_LOBBY: 'lobby',
        CosinnusConferenceRoom.TYPE_STAGE: 'stage',
        CosinnusConferenceRoom.TYPE_WORKSHOPS: 'workshops',
        CosinnusConferenceRoom.TYPE_DISCUSSIONS: 'discussions',
        CosinnusConferenceRoom.TYPE_COFFEE_TABLES: 'coffee_tables',
        CosinnusConferenceRoom.TYPE_RESULTS: 'results',
    }
    type = serializers.SerializerMethodField()
    count = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    management_urls = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusConferenceRoom
        fields = ('id', 'slug', 'title', 'description', 'type', 'count', 'url', 'management_urls')

    def get_type(self, obj):
        return self.TYPE_MAP.get(obj.type)

    def get_count(self, obj):
        if obj.type == obj.TYPE_LOBBY:
            return ConferenceEvent.objects.conference_upcoming().filter(group=obj.group).count()
        else:
            return obj.events.conference_upcoming().count()

    def get_url(self, obj):
        if obj.type == obj.TYPE_RESULTS and obj.target_result_group:
            return obj.target_result_group.get_absolute_url()
        else:
            return obj.get_rocketchat_room_url()

    def get_management_urls(self, obj):
        user = self.context['request'].user
        if check_ug_admin(user, obj.group) or check_user_superuser(user):
            return {
                'create_event': obj.get_room_create_url(),
                'update_room': obj.get_edit_url(),
                'delete_room': obj.get_delete_url(),
            }
        return {}


class ConferenceSerializer(serializers.HyperlinkedModelSerializer):
    rooms = serializers.SerializerMethodField()
    management_urls = serializers.SerializerMethodField()
    theme_color = serializers.CharField(source='conference_theme_color')

    class Meta(object):
        model = CosinnusGroup
        fields = ('id', 'name', 'description', 'rooms', 'management_urls', 'theme_color')

    def get_rooms(self, obj):
        rooms = obj.rooms.all()
        request = self.context['request']
        if not check_ug_admin(request.user, obj):
            rooms = rooms.visible()
        serializer = ConferenceRoomSerializer(instance=rooms, many=True, context={'request': request})
        return serializer.data

    def get_management_urls(self, obj):
        user = self.context['request'].user
        if check_ug_admin(user, obj) or check_user_superuser(user):
            return {
                'manage_conference': group_aware_reverse('cosinnus:conference:management', kwargs={'group': obj}),
                'manage_rooms': group_aware_reverse('cosinnus:conference:room-management', kwargs={'group': obj})
            }
        return ""


class ConferenceParticipant(serializers.ModelSerializer):
    organisation = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta(object):
        model = get_user_model()
        fields = ('first_name', 'last_name', 'organisation', 'location')

    def get_organisation(self, obj):
        return ""

    def get_location(self, obj):
        return obj.cosinnus_profile.media_tag.location


class ConferenceEventRoomSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = CosinnusConferenceRoom
        fields = ('id', 'title', 'slug')


class ConferenceEventSerializer(serializers.ModelSerializer):
    room = ConferenceEventRoomSerializer()
    url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    participants_count = serializers.SerializerMethodField()
    management_urls = serializers.SerializerMethodField()

    class Meta(object):
        model = ConferenceEvent
        fields = ('id', 'title', 'note', 'from_date', 'to_date', 'room', 'url', 'is_break', 'image_url',
                  'participants_count', 'participants', 'management_urls')
    # change: title, note, from_date, to_date

    def get_url(self, obj):
        # FIXME: Maybe smarter filtering for URL
        return obj.url or obj.get_bbb_room_url()

    def get_image_url(self, obj):
        image_file = obj.attached_image.file if obj.attached_image else None
        if image_file:
            return image_thumbnail_url(image_file, (466, 112))
        return static('images/conference-event-placeholder.png')

    def get_participants(self, obj):
        # participants = obj.participants.all()
        # serializer = ConferenceParticipant(instance=participants, many=True,
        #                                    context={'request': self.context['request']})
        # return serializer.data
        return []

    def get_participants_count(self, obj):
        return 0

    def get_management_urls(self, obj):
        user = self.context['request'].user
        if check_ug_admin(user, obj.group) or check_user_superuser(user):
            return {
                'create_event': obj.room.get_room_create_url(),
                'update_event': obj.get_edit_url(),
                'delete_event': obj.get_delete_url(),
            }
        return {}

"""

            {
                "id": 1,
                "name": "Check In",
                "description": "Try the public Chat LOBBY or ask for help: TEAM SUPPORT",
                "from_time": "2020-09-14 08:30:00 UTC",
                "to_time": "2020-09-14 09:15:00 UTC",
                "room_name": "Chat LOBBY",
                "room_slug": "lobby",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
"""