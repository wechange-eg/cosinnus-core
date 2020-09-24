# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import timedelta
from builtins import object
import random

from cosinnus.templatetags.cosinnus_tags import textfield
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Max, Min
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
        CosinnusConferenceRoom.TYPE_PARTICIPANTS: 'participants',
    }
    type = serializers.SerializerMethodField()
    count = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    description_html = serializers.SerializerMethodField()
    management_urls = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusConferenceRoom
        fields = ('id', 'slug', 'title', 'description_html', 'type', 'count', 'url', 'management_urls', 'is_visible')

    def get_type(self, obj):
        return self.TYPE_MAP.get(obj.type)

    def get_count(self, obj):
        if obj.type == obj.TYPE_PARTICIPANTS:
            return obj.group.users.filter(is_active=True).count()
        elif obj.type == obj.TYPE_LOBBY:
            queryset = ConferenceEvent.objects.filter(group=obj.group).exclude(type__in=ConferenceEvent.TIMELESS_TYPES)
            return queryset.conference_upcoming().count()
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

    def get_description_html(self, obj):
        return textfield(obj.description)


class ConferenceSerializer(serializers.HyperlinkedModelSerializer):
    rooms = serializers.SerializerMethodField()
    management_urls = serializers.SerializerMethodField()
    theme_color = serializers.CharField(source='conference_theme_color')
    dates = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusGroup
        fields = ('id', 'name', 'description', 'rooms', 'management_urls', 'theme_color', 'dates')

    def get_rooms(self, obj):
        rooms = obj.rooms.all()
        request = self.context['request']
        if not (check_ug_admin(request.user, obj) or check_user_superuser(request.user)):
            rooms = rooms.visible()
        serializer = ConferenceRoomSerializer(instance=rooms, many=True, context={'request': request})
        return serializer.data

    def get_management_urls(self, obj):
        user = self.context['request'].user
        if check_ug_admin(user, obj) or check_user_superuser(user):
            return {
                'manage_conference': group_aware_reverse('cosinnus:conference:management', kwargs={'group': obj}),
                'manage_rooms': group_aware_reverse('cosinnus:conference:room-management', kwargs={'group': obj}),
                'manage_events': group_aware_reverse('cosinnus:event:conference-event-list', kwargs={'group': obj}),
            }
        return ""

    def get_dates(self, obj):
        queryset = ConferenceEvent.objects.filter(room__group=obj)
        queryset = queryset.aggregate(Min('from_date'), Max('to_date'))
        from_date, to_date = queryset['from_date__min'].date(), queryset['to_date__max'].date()
        return [from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)]


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
    type = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusConferenceRoom
        fields = ('id', 'title', 'slug', 'type')

    def get_type(self, obj):
        return ConferenceRoomSerializer.TYPE_MAP.get(obj.type)


class ConferenceParticipantSerializer(serializers.ModelSerializer):
    organisation = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    chat_url = serializers.SerializerMethodField()

    class Meta(object):
        model = get_user_model()
        fields = ('id', 'first_name', 'last_name', 'organisation', 'country', 'chat_url')
        order_by = ('first_name', 'last_name')

    def get_organisation(self, obj):
        if hasattr(obj, 'cosinnus_profile'):
            return random.choice(["A", "B", "C"])
            # return obj.cosinnus_profile.organisation
        return ""

    def get_country(self, obj):
        if hasattr(obj, 'cosinnus_profile'):
            return random.choice(["Germany", "Russia", "Belarus"])
            # return obj.cosinnus_profile.country
        return ""

    def get_chat_url(self, obj):
        if hasattr(obj, 'cosinnus_profile'):
            return f'{settings.COSINNUS_CHAT_BASE_URL}/direct/{obj.cosinnus_profile.rocket_username}/?layout=embedded'
        else:
            return settings.COSINNUS_CHAT_BASE_URL


class ConferenceEventParticipantSerializer(serializers.ModelSerializer):

    class Meta(object):
        model = get_user_model()
        fields = ('first_name', 'last_name')


class ConferenceEventSerializer(serializers.ModelSerializer):
    room = ConferenceEventRoomSerializer()
    url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    presenters = ConferenceEventParticipantSerializer(many=True)
    participants_limit = serializers.IntegerField(source='max_participants')
    participants_count = serializers.SerializerMethodField()
    management_urls = serializers.SerializerMethodField()
    note_html = serializers.SerializerMethodField()

    class Meta(object):
        model = ConferenceEvent
        fields = ('id', 'title', 'note_html', 'from_date', 'to_date', 'room', 'url', 'is_break', 'image_url',
                  'presenters', 'participants_limit', 'participants_count', 'management_urls')

    def get_url(self, obj):
        # FIXME: Maybe smarter filtering for URL
        return obj.url or obj.get_bbb_room_url()

    def get_image_url(self, obj):
        image_file = obj.attached_image.file if obj.attached_image else None
        if image_file:
            return image_thumbnail_url(image_file, (466, 112))
        return static('images/conference-event-placeholder.png')

    def get_participants_count(self, obj):
        if obj.media_tag and obj.media_tag.bbb_room:
            return obj.media_tag.bbb_room.remote_user_count
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

    def get_note_html(self, obj):
        return textfield(obj.note)

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