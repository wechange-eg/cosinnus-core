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
from django.utils.translation import gettext_lazy as _, get_language
from django.template.loader import render_to_string
from django.template.defaultfilters import linebreaksbr
from django.template.context import Context
from cosinnus.models.managed_tags import CosinnusManagedTagAssignment
from django.template.defaultfilters import date as date_format


__all__ = ('ConferenceSerializer', )

from cosinnus.utils.files import image_thumbnail_url

from cosinnus.utils.permissions import check_ug_admin, check_user_superuser,\
    check_ug_membership
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_event.models import ConferenceEvent # noqa


class _TranslatedInstanceMixin():
    
    def to_representation(self, instance):
        """ Support for `TranslateableFieldsModelMixin` """
        self.untranslated_instance = instance
        if hasattr(instance, 'get_translated_readonly_instance'):
            instance = instance.get_translated_readonly_instance()
        return super().to_representation(instance)


class TranslateableModelSerializer(_TranslatedInstanceMixin, serializers.ModelSerializer):
    """ A model serializer that works well with returning translated fields
        for any models inheriting `TranslateableFieldsModelMixin` """
    pass


class TranslateableHyperlinkedModelSerializer(_TranslatedInstanceMixin, serializers.HyperlinkedModelSerializer):
    """ A model serializer that works well with returning translated fields
        for any models inheriting `TranslateableFieldsModelMixin` """
    pass
    
class ConferenceRoomSerializer(TranslateableModelSerializer):
    
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
    show_chat = serializers.SerializerMethodField()
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
            return obj.group.actual_members.count()
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
            # for the result room's project, check if it defines an alternate sub-URL in its settings 
            # to be shown in the iframe 
            result_group = obj.target_result_group
            return result_group.get_absolute_url() + result_group.settings.get('conference_result_group_iframe_url', '')
        else:
            # we need to use the untranslated instance, because this function might save the instance
            user = self.context['request'].user
            if not user.is_authenticated or user.is_guest:
                return None
            return self.untranslated_instance.get_rocketchat_room_url()
    
    def get_show_chat(self, obj):
        """ Returns true if the show chat checkboxes on the room are set
            and the room has a rocketchat url """
        user = self.context['request'].user
        if not user.is_authenticated or user.is_guest:
            return False
        return bool(obj.show_chat and self.untranslated_instance.get_rocketchat_room_url())
    
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


class ConferenceSerializer(TranslateableHyperlinkedModelSerializer):
    rooms = serializers.SerializerMethodField()
    management_urls = serializers.SerializerMethodField()
    theme_color = serializers.SerializerMethodField()
    dates = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    wallpaper = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    header_notification = serializers.SerializerMethodField()
    managed_tags = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusGroup
        fields = ('id', 'name', 'description', 'rooms', 'management_urls', 'theme_color', 'dates', 'avatar',
                  'wallpaper', 'images', 'header_notification', 'managed_tags', 'url', 'from_date', 'to_date',
                  'subtitle')
    
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
        if settings.COSINNUS_PREMIUM_CONFERENCES_ENABLED and (check_ug_admin(user, obj) or check_user_superuser(user)):
            if obj.has_premium_blocks or obj.is_premium:
                if obj.is_premium:
                    notification_text = _('Your conference is currently using the high performance premium servers!')
                    notification_severity = 'success'
                else:
                    notification_text = _('Your conference is currently not using the high performance premium servers, but has been assigned premium slots at other times.')
                    notification_severity = 'info'
                    
                if obj.has_premium_blocks:
                    premium_block_dates = []
                    for premium_block in obj.conference_premium_blocks.all():
                        str_date = date_format(premium_block.from_date, 'SHORT_DATE_FORMAT')
                        if premium_block.from_date != premium_block.to_date:
                            str_date += ' - ' + date_format(premium_block.to_date, 'SHORT_DATE_FORMAT')
                        premium_block_dates.append(str_date)
                    if premium_block_dates:
                        notification_text = str(notification_text) + '<br/>' + \
                                str(_('Your currently scheduled premium dates are:')) + ' ' + ', '.join(premium_block_dates)
            else:
                notification_text = _('Your conference is still in trial mode. You have access to all features, but can only use them with a few people without restrictions. To ensure full performance for your conference with multiple users, book sufficient capacities here for free:')
                notification_severity = 'warning'
            header_notification = {
                'notification_text': notification_text,
                'notification_severity': notification_severity,
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
    
    def get_avatar(self, obj):
        domain = obj.portal.get_domain()
        return (domain + obj.avatar.url) if obj.avatar else None
    
    def get_wallpaper(self, obj):
        domain = obj.portal.get_domain()
        return (domain + obj.wallpaper.url) if obj.wallpaper else None

    def get_images(self, obj):
        domain = obj.portal.get_domain()
        return [(domain + img.file.url) for img in obj.attached_images]
    
    def get_managed_tags(self, obj):
        return [tag.slug for tag in obj.get_managed_tags()]
    
    def get_url(self, obj):
        return obj.get_absolute_url()
    
    def get_theme_color(self, obj):
        return obj.conference_theme_color or settings.COSINNUS_CONFERENCES_DEFAULT_THEME_COLOR


class ConferenceParticipant(TranslateableModelSerializer):
    organization = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta(object):
        model = get_user_model()
        fields = ('first_name', 'last_name', 'organization', 'location')

    def get_organization(self, obj):
        return ""

    def get_location(self, obj):
        return obj.cosinnus_profile.media_tag.location


class ConferenceEventRoomSerializer(TranslateableModelSerializer):
    type = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusConferenceRoom
        fields = ('id', 'title', 'slug', 'type')

    def get_type(self, obj):
        return ConferenceRoomSerializer.TYPE_MAP.get(obj.type)


class ConferenceParticipantSerializer(TranslateableModelSerializer):
    organization = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    chat_url = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    profile_url = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta(object):
        model = get_user_model()
        fields = ('id', 'first_name', 'last_name', 'organization',
                  'country', 'chat_url', 'avatar_url', 'profile_url', 'location')
        order_by = ('first_name', 'last_name')

    def get_organization(self, obj):
        if hasattr(obj, 'cosinnus_profile'):
            # Temporary hack: Allow the organization field to come from a different attribute
            att_name = getattr(settings, 'COSINNUS_TEMPHACK_CONFERENCE_ORGANIZATION_SOURCE_FIELD_NAME', 'organization')
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

    def get_avatar_url(self, obj):
        if hasattr(obj, 'cosinnus_profile'):
            return obj.cosinnus_profile.get_avatar_thumbnail_url()
        return ''

    def get_profile_url(self, obj):
        if hasattr(obj, 'cosinnus_profile'):
            return obj.cosinnus_profile.get_absolute_url()
        return ''

    def get_location(self, obj):
        if hasattr(obj, 'cosinnus_profile'):
            if obj.cosinnus_profile.media_tag.location:
                return obj.cosinnus_profile.media_tag.location
        return ''


class ConferenceEventParticipantSerializer(TranslateableModelSerializer):

    class Meta(object):
        model = get_user_model()
        fields = ('first_name', 'last_name')


class ConferenceEventSerializer(TranslateableModelSerializer):
    room = ConferenceEventRoomSerializer()
    url = serializers.SerializerMethodField()
    is_queue_url = serializers.SerializerMethodField() 
    image_url = serializers.SerializerMethodField()
    presenters = ConferenceEventParticipantSerializer(many=True)
    participants_limit = serializers.SerializerMethodField()
    management_urls = serializers.SerializerMethodField()
    note_html = serializers.SerializerMethodField()
    feed_url = serializers.SerializerMethodField()
    show_chat = serializers.SerializerMethodField()
    chat_url = serializers.SerializerMethodField()
    user_is_admin = serializers.SerializerMethodField()

    class Meta(object):
        model = ConferenceEvent
        fields = ('id', 'title', 'note_html', 'from_date', 'to_date', 'room', 'url', 'is_queue_url', 'raw_html', 'is_break',
                  'image_url', 'presenters', 'participants_limit', 'feed_url', 'management_urls', 'show_chat', 'chat_url',
                  'user_is_admin')

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
        return group_aware_reverse('cosinnus:team-conference-event-entry', kwargs={'team_id': obj.group.id,
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
    
    def get_participants_limit(self, obj):
        return obj.get_max_participants()
    
    def get_show_chat(self, obj):
        """ Returns true if the show chat checkboxes on the event and its room are set
            and the room as a rocketchat url """
        user = self.context['request'].user
        if not user.is_authenticated or user.is_guest:
            return False
        return bool(obj.show_chat and obj.room.show_chat and obj.room.get_rocketchat_room_url())
    
    def get_chat_url(self, obj):
        """ Returns the event room's URL if the show chat checkboxes on the event and its room are set
            and the room as a rocketchat url """
        user = self.context['request'].user
        if not user.is_authenticated or user.is_guest:
            return None
        return obj.show_chat and obj.room.show_chat and obj.room.get_rocketchat_room_url()

    def get_user_is_admin(self, obj):
        """ Returns if user is event admin or superuser. """
        user = self.context['request'].user
        return check_ug_admin(user, obj.group) or check_user_superuser(user)


class ConferenceEventParticipantsSerializer(TranslateableModelSerializer):
    participants_count = serializers.SerializerMethodField()

    class Meta(object):
        model = ConferenceEvent
        fields = ('id', 'participants_count')

    def get_participants_count(self, obj):
        if obj.media_tag and obj.media_tag.bbb_room:
            return obj.media_tag.bbb_room.remote_user_count
        return 0
