# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import timedelta
from builtins import object
import random

from django.urls import reverse

from cosinnus.templatetags.cosinnus_tags import textfield, get_country_name
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Max, Min
from rest_framework import serializers

from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.models.group import CosinnusGroup
from django.templatetags.static import static
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, get_language
from django.template.loader import render_to_string
from django.template.context import Context
from cosinnus.models.managed_tags import CosinnusManagedTagAssignment


__all__ = ('ConferenceSerializer', )

from cosinnus.utils.files import image_thumbnail_url

from cosinnus.utils.permissions import check_ug_admin, check_user_superuser,\
    check_ug_membership
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
        fields = ('id', 'slug', 'title', 'description_html', 'type', 'count', 'url', 'management_urls', 
                  'is_visible', 'show_chat')

    def get_type(self, obj):
        return self.TYPE_MAP.get(obj.type)

    def get_count(self, obj):
        if obj.type == obj.TYPE_PARTICIPANTS:
            return obj.group.users.filter(is_active=True).count()
        return 0
        # Note: room event counts are disabled for now, as they are confusing users to
        # think that the number actually means participant counts
        """
        elif obj.type == obj.TYPE_LOBBY:
            queryset = ConferenceEvent.objects.filter(group=obj.group)\
                .exclude(type__in=ConferenceEvent.TIMELESS_TYPES)\
                .filter(room__is_visible=True)
            return queryset.count()
        else:
            return obj.events.count()
        """

    def get_url(self, obj):
        if obj.type == obj.TYPE_RESULTS and obj.target_result_group:
            return obj.target_result_group.get_absolute_url()
        else:
            return obj.get_rocketchat_room_url()

    def get_management_urls(self, obj):
        user = self.context['request'].user
        if check_ug_admin(user, obj.group) or check_user_superuser(user):
            management_urls = {
                'update_room': obj.get_edit_url(),
                'delete_room': obj.get_delete_url(),
            }
            # Lobby room types do not have a "Create Event" button
            if obj.type != CosinnusConferenceRoom.TYPE_LOBBY:
                management_urls.update({
                    'create_event': obj.get_room_create_url(),
                })
            return management_urls
        return {}

    def get_description_html(self, obj):
        return textfield(obj.description)


class ConferenceSerializer(serializers.HyperlinkedModelSerializer):
    rooms = serializers.SerializerMethodField()
    management_urls = serializers.SerializerMethodField()
    theme_color = serializers.CharField(source='conference_theme_color')
    dates = serializers.SerializerMethodField()
    avatar = serializers.CharField(source='avatar_url')
    wallpaper = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    header_notification = serializers.SerializerMethodField()
    managed_tags = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusGroup
        fields = ('id', 'name', 'description', 'rooms', 'management_urls', 'theme_color', 'dates', 'avatar',
                  'wallpaper', 'images', 'header_notification', 'managed_tags')

    def get_rooms(self, obj):
        rooms = obj.rooms.all()
        request = self.context['request']
        if not (check_ug_admin(request.user, obj) or check_user_superuser(request.user)):
            rooms = rooms.visible()
        serializer = ConferenceRoomSerializer(instance=rooms, many=True, context={'request': request})
        return serializer.data

    def get_management_urls(self, obj):
        user = self.context['request'].user
        management_urls = {}
        # available for all members
        if check_ug_membership(user, obj) or check_user_superuser(user):
            management_urls.update({
                'manage_memberships': group_aware_reverse('cosinnus:group-detail', kwargs={'group': obj})
            })
        if check_ug_admin(user, obj) or check_user_superuser(user):
            management_urls.update({
                'manage_conference': group_aware_reverse('cosinnus:group-edit', kwargs={'group': obj}),
                'manage_rooms': group_aware_reverse('cosinnus:conference:room-management', kwargs={'group': obj}),
                'manage_events': group_aware_reverse('cosinnus:event:conference-event-list', kwargs={'group': obj}),
            })
        return management_urls
    
    def get_header_notification(self, obj):
        user = self.context['request'].user
        # show a premium notification for admins
        if (settings.COSINNUS_PREMIUM_CONFERENCES_ENABLED and not obj.is_premium) \
                and (check_ug_admin(user, obj) or check_user_superuser(user)):
            header_notification = {
                'notification_text': _('Your conference is still in trial mode. You have access to all features, but can only use them with a few people without restrictions. To ensure full performance for your conference with multiple users, book sufficient capacities here for free:'),
                'link_text': _('Conference Bookings'),
                'link_url': render_to_string('cosinnus/v2/urls/conference_premium_booking_url.html', context={
                                'COSINNUS_CURRENT_LANGUAGE': get_language(),
                            }),
            }
            return header_notification
        return {}

    def get_dates(self, obj):
        queryset = ConferenceEvent.objects.filter(room__group=obj)
        if queryset.count() > 0:
            queryset = queryset.aggregate(Min('from_date'), Max('to_date'))
            from_date = queryset['from_date__min'].date() if queryset['from_date__min'] else now()
            to_date = queryset['to_date__max'].date() if queryset['to_date__max'] else from_date
        else:
            from_date, to_date = now(), now()
        return [from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)]

    def get_wallpaper(self, obj):
        return obj.wallpaper.url if obj.wallpaper else None

    def get_images(self, obj):
        return [img.image.url for img in obj.gallery_images.all()]
    
    def get_managed_tags(self, obj):
        return [tag.slug for tag in obj.get_managed_tags()]
    

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
            # Temporary hack: Allow the organisation field to come from a different attribute
            att_name = getattr(settings, 'COSINNUS_TEMPHACK_CONFERENCE_ORGANISATION_SOURCE_FIELD_NAME', 'organisation')
            return obj.cosinnus_profile.dynamic_fields.get(att_name, "")
        return ""

    def get_country(self, obj):
        if hasattr(obj, 'cosinnus_profile'):
            country_code = obj.cosinnus_profile.dynamic_fields.get('country', "")
            if country_code:
                return get_country_name(country_code)
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
    is_queue_url = serializers.SerializerMethodField() 
    image_url = serializers.SerializerMethodField()
    presenters = ConferenceEventParticipantSerializer(many=True)
    participants_limit = serializers.IntegerField(source='max_participants')
    management_urls = serializers.SerializerMethodField()
    note_html = serializers.SerializerMethodField()
    feed_url = serializers.SerializerMethodField()

    class Meta(object):
        model = ConferenceEvent
        fields = ('id', 'title', 'note_html', 'from_date', 'to_date', 'room', 'url', 'is_queue_url', 'raw_html', 'is_break',
                  'image_url', 'presenters', 'participants_limit', 'feed_url', 'management_urls')

    def get_url(self, obj):
        # FIXME: Maybe smarter filtering for URL
        return obj.url or obj.get_bbb_room_queue_api_url()
    
    def get_is_queue_url(self, obj):
        """ See `get_url` logic. If we have a direct URL in the event, this is False,
            so the url is set directly into the iFrame. """
        return not bool(obj.url)

    def get_image_url(self, obj):
        image_file = obj.attached_image.file if obj.attached_image else None
        if image_file:
            return image_thumbnail_url(image_file, (466, 112))
        return static('images/conference-event-placeholder.png')

    def get_feed_url(self, obj):
        return group_aware_reverse('cosinnus:event:conference-event-entry', kwargs={'group': obj.group.slug,
                                                                                    'slug': obj.slug})

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


class ConferenceEventParticipantsSerializer(serializers.ModelSerializer):
    participants_count = serializers.SerializerMethodField()

    class Meta(object):
        model = ConferenceEvent
        fields = ('id', 'participants_count')

    def get_participants_count(self, obj):
        if obj.media_tag and obj.media_tag.bbb_room:
            return obj.media_tag.bbb_room.remote_user_count
        return 0
