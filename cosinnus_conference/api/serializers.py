# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from django.contrib.auth import get_user_model
from rest_framework import serializers

from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.models.group import CosinnusGroup


__all__ = ('ConferenceSerializer', )

from cosinnus.utils.files import image_thumbnail_url

from cosinnus.utils.permissions import check_ug_admin
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
    url = serializers.URLField(source='get_rocketchat_room_url')

    class Meta(object):
        model = CosinnusConferenceRoom
        fields = ('id', 'slug', 'title', 'description', 'type', 'count', 'url')

    def get_type(self, obj):
        return self.TYPE_MAP.get(obj.type)

    def get_count(self, obj):
        return obj.events.all().count()


class ConferenceSerializer(serializers.HyperlinkedModelSerializer):
    rooms = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusGroup
        fields = ('name', 'description', 'rooms')

    def get_rooms(self, obj):
        rooms = obj.rooms.all()
        if not check_ug_admin(self.context['request'].user, obj):
            rooms = rooms.visible()
        serializer = ConferenceRoomSerializer(instance=rooms, many=True, context={'request': self.context['request']})
        return dict([(r['slug'], r) for r in serializer.data])


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

    class Meta(object):
        model = ConferenceEvent
        fields = ('id', 'title', 'note', 'from_date', 'to_date', 'room', 'url', 'image_url',
                  'participants_count', 'participants')
    # change: title, note, from_date, to_date

    def get_url(self, obj):
        # FIXME: Maybe smarter filtering for URL
        return obj.url or obj.get_bbb_room_url()

    def get_image_url(self, obj):
        image_file = obj.attached_image.file if obj.attached_image else None
        if image_file:
            return image_thumbnail_url(image_file, (466, 112))
        return ""

    def get_participants(self, obj):
        # participants = obj.participants.all()
        # serializer = ConferenceParticipant(instance=participants, many=True,
        #                                    context={'request': self.context['request']})
        # return serializer.data
        return []

    def get_participants_count(self, obj):
        return 0
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