import logging
import random
import string

from annoying.functions import get_object_or_None
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields.jsonb import JSONField as PostgresJSONField
from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls.base import reverse
from django.utils import timezone
from django.utils.translation import ugettext as _

from cosinnus.apis.bigbluebutton import BigBlueButtonAPI
from cosinnus.templatetags.cosinnus_tags import full_name
from cosinnus.utils import bigbluebutton as bbb_utils
from cosinnus.utils.permissions import check_user_superuser
from datetime import timedelta
from django.utils.timezone import now
from django.http.response import HttpResponseForbidden
from django.utils.crypto import get_random_string
from cosinnus.models.group import CosinnusPortal
from django.core.exceptions import ImproperlyConfigured
from pip._internal.cli.cmdoptions import editable


# from cosinnus.models import MEMBERSHIP_ADMIN
logger = logging.getLogger('cosinnus')


def random_meeting_id():
    """ Function is needed for old migrations """
    bbb_utils.random_meeting_id()


def random_password(length=5):
    """ Function is needed for old migrations """
    return bbb_utils.random_password(length)


def random_voice_bridge():
    """ Function is needed for old migrations """
    return bbb_utils.random_voice_bridge()


class BBBRoom(models.Model):
    """ This model represents a video/audio conference call with participants and/or presenters
    
    :var portal: The base portal
    :type: group.CosinusBaseGroup
    
    :var presenter: User that has the presenter role if any
    :type: auth.User

    :var members: Users, that can join the meeting
    :type: list of auth.User

    :var moderators: Users with moderator/admin permissions for this meeting
    :type: list of auth.User

    :var name: (optional) name of the room
    :type: str

    :var moderator_password: password to enter a conversation as moderator
    :type: str

    :var attendee_password: password to enter a conversation as moderator
    :type: str

    :var welcome_message: Message that is displayed when enterin the conversation
    :type: str

    :var max_attendees: Message that is displayed when enterin the conversation
    :type: str
    """
    portal = models.ForeignKey('cosinnus.CosinnusPortal', verbose_name=_('Portal'), related_name='bbb_rooms', 
        null=False, blank=False, default=1, on_delete=models.CASCADE) # port_id 1 is created in a datamigration!

    presenter = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="presenter",
                                  help_text=_("this user will enter the BBB presenter mode for this conversation"))
    attendees = models.ManyToManyField(User, related_name="attendees")
    moderators = models.ManyToManyField(User)
    meeting_id = models.CharField(max_length=200, unique=True, default=bbb_utils.random_meeting_id)
    name = models.CharField(max_length=160, null=True, blank=True, verbose_name=_("room name or title"))
    moderator_password = models.CharField(max_length=30, default=bbb_utils.random_password,
                                          help_text=_("the password set to enter the room as a moderator"))
    attendee_password = models.CharField(max_length=30, default='', null=True, blank=True,
                                         help_text=_("the password set to enter the room as a attendee"))
    dial_number = models.CharField(blank=True, null=True, default="", max_length=20,
                                   help_text=_("number for dialing into the conference via telephone"),
                                   verbose_name="telephone dial in number")
    voice_bridge = models.PositiveIntegerField(help_text=_("pin to enter for telephone participants"),
                                               verbose_name="dial in PIN", default=bbb_utils.random_voice_bridge,
                                               validators=[MinValueValidator(10000), MaxValueValidator(99999)])
    internal_meeting_id = models.CharField(max_length=100, blank=True, null=True)
    parent_meeting_id = models.CharField(max_length=100, blank=True, null=True)
    ended = models.BooleanField(default=False)
    
    
    # deprecated in favor of deriving create options directly from the source event!
    options = JSONField(blank=True, null=True, default=dict, verbose_name="room options",
                        editable=False,
                        help_text=_("DEPRECATED! options for the room, that are represented in the bigbluebutton API"))
    # deprecated in favor of deriving create options directly from the source event!
    welcome_message = models.CharField(max_length=300, null=True, blank=True, verbose_name=_("the rooms welcome message"),
                                       editable=False,
                                       help_text=_("DEPRECATED! the welcome message, that is displayed to attendees"))
    # deprecated in favor of deriving create options directly from the source event!
    # type of the room. this determines which extra join call parameters are given
    # along for the user join link. see `settings.BBB_ROOM_TYPE_EXTRA_JOIN_PARAMETERS`
    room_type = models.PositiveSmallIntegerField(_('Room Type'), blank=False,
        editable=False,
        default=settings.BBB_ROOM_TYPE_DEFAULT, choices=settings.BBB_ROOM_TYPE_CHOICES,
        help_text="DEPRECATED!")
    # deprecated in favor of deriving create options directly from the source event!
    max_participants = models.PositiveIntegerField(blank=True, null=True, default=None, verbose_name="maximum number of users",
                                                   editable=False,
                                                   help_text="Maximum number in the conference at the same time. NOTE: Seems this needs to be +1 more the number that you actually want for BBB to allow!")
    
    
    objects = models.Manager()
    
    # cache key for each rooms participants
    PARTICIPANT_COUNT_CACHE_KEY = 'cosinnus/core/bbbroom/%d/participants' # bbb-room-id
    
    # the BigBlueButtonAPI instance for this room
    _bbb_api = None
    
    # the cached source ConferenceEvent instance for this room
    _event = '__unset__'

    def __str__(self):
        return str(self.meeting_id)
    
    @property
    def bbb_api(self):
        if self._bbb_api is None:
            # initialize bbb api instance with this room
            self._bbb_api = BigBlueButtonAPI(source_object=self)
        return self._bbb_api
    
    def save(self, *args, **kwargs):
        """ Assign current portal """
        created = bool(self.pk is None)
        if created and not self.portal:
            from cosinnus.models.group import CosinnusPortal
            self.portal = CosinnusPortal.get_current()
        super(BBBRoom, self).save(*args, **kwargs)

    def end(self):
        self.bbb_api.end_meeting(self.meeting_id, self.moderator_password)
        self.ended = True
        self.save()
    
    def retrieve_remote_user_count(self):
        """ Non-cached function to retrieve the remote user count for this meeting """
        try:
            meeting_info = self.bbb_api.meeting_info(self.meeting_id, self.moderator_password)
            if not meeting_info:
                return 0
            return meeting_info.get('participantCount', 0)
        except Exception as e:
            if settings.DEBUG:
                raise
            logger.exception(e)
            return 0
    
    @property
    def remote_user_count(self):
        """ Cached function that can be called often, to get the very-recent
            user count for this meeting """
        if not self.id:
            return 0
        count = cache.get(self.PARTICIPANT_COUNT_CACHE_KEY % self.id)
        if count is None:
            count = self.retrieve_remote_user_count()
            cache.set(self.PARTICIPANT_COUNT_CACHE_KEY % self.id, count, settings.BBB_ROOM_PARTICIPANTS_CACHE_TIMEOUT_SECONDS)
        return count

    def get_password_for_user(self, user):
        """ returns the room password according to the permission of a given user.
        Returns empty string, if user is no member of the room

        :return: password for the user to join the room
        :rtype: str
        """
        if check_user_superuser(user) or user in self.moderators.all():
            return self.moderator_password
        elif user in self.attendees.all():
            return self.attendee_password
        else:
            return ''
    
    def check_user_can_enter_room(self, user):
        """ Checks if a user has the neccessary permissions to enter this room """
        return bool(user.is_authenticated and self.get_password_for_user(user))

    def remove_user(self, user):
        self.moderators.remove(user)
        self.attendees.remove(user)
        
    def remove_all_users(self):
        self.moderators.clear()
        self.attendees.clear()

    def join_user(self, user, as_moderator=False):
        if as_moderator:
            self.moderators.add(user)
            self.attendees.remove(user)
        else:
            self.attendees.add(user)
            self.moderators.remove(user)

    def join_group_members(self, group):
        for membership in group.memberships.all():
            # FIXME: reference group MEMBER_STATUS etc
            if membership.status in (1, 2,):
                self.join_user(membership.user, as_moderator=bool(membership.status==2))

    @property
    def members(self):
        return self.moderators.all() | self.attendees.all()
    
    @property
    def is_running(self):
        """ Checks if a meeting is currently running on the server
            (as opposed to never started or suspended) """
        if self.meeting_id and self.attendee_password:
            try:
                meeting_info = self.bbb_api.meeting_info(self.meeting_id, self.attendee_password) 
                if meeting_info and meeting_info.get('running', False) == 'true':
                    return True
            except Exception as e:
                logger.exception(e)
        return False

    @property
    def event(self):
        """ Tries to get a conference event for this bbb room, or returns None else """
        if self._event == '__unset__':
            from cosinnus_event.models import ConferenceEvent # noqa
            media_tag = self.tagged_objects.first()
            # TODO: if other event types can carry BBBRooms, replace the `ConferenceEvent` here!
            self._event = get_object_or_None(ConferenceEvent, media_tag=media_tag)
        return self._event

    def restart(self):
        event = self.event
        m_xml = self.bbb_api.start(
            name=self.name,
            meeting_id=self.meeting_id,
            attendee_password=self.attendee_password,
            moderator_password=self.moderator_password,
            voice_bridge=self.voice_bridge,
            options=self.build_extra_create_parameters(),
            presentation_url=event.presentation_file.url if event and event.presentation_file else None,
        )

        meeting_json = bbb_utils.xml_to_json(m_xml)

        if not meeting_json:
            raise ValueError('Unable to restart meeting %s!' % self.meeting_id)

        if self.ended:
            self.ended = False
            self.save(update_fields=['ended'])

        return None

    @classmethod
    def create(cls, name, meeting_id, attendee_password=None,
               moderator_password=None, voice_bridge=None,
               presentation_url=None, source_object=None):
        """ Creates a new BBBRoom and crete a room on the remote bbb-server.

        :param name: Name of the BBBRoom
        :type: str

        :param meeting_id: ID on the BBB-Server. Must be unique for any meeting running on the BBB-Server
        :type: str

        :param meeting_welcome: Welcome message displayed at start of the meeting
        :type: str

        :param attendee_password: Password for joining the meeting with attendee rights
        :type: str

        :param moderator_password: Password for joining the meeting with moderator rights
        :type: str

        :param voice_bridge: Dial in PIN for joining the meeting via telephone call
        :type: int range(10000 - 99999)

        :param presentation_url: Publicly available URL of presentation file to be pre-uploaded as slides to BBB room
        :type: str
        
        :param source_object: The object the room is attached to. Check `CosinnusConferenceSettings.get_for_object()` for valid arguments.

        :type: dict
        """
        
        from cosinnus.models.group import CosinnusPortal
        current_portal = CosinnusPortal.get_current()
        
        # Do not create a meeting if one already exists
        existing_meeting = get_object_or_None(BBBRoom, meeting_id=meeting_id, portal=current_portal)
        if existing_meeting:
            existing_meeting.restart()
            return existing_meeting
        
        # add a suffix to uniquify this meeting id - makes it safe for manual restarts
        # by deleting the BBBRoom object
        meeting_id = f'{meeting_id}-' + get_random_string(8)
        
        if attendee_password is None:
            attendee_password = bbb_utils.random_password()
        if moderator_password is None:
            moderator_password = bbb_utils.random_password()

        bbb_api = BigBlueButtonAPI(source_object=source_object)
        m_xml = bbb_api.start(
            name=name,
            meeting_id=meeting_id,
            attendee_password=attendee_password,
            moderator_password=moderator_password,
            voice_bridge=voice_bridge,
            options=cls.build_extra_create_parameters_for_object(source_object),
            presentation_url=presentation_url,
        )

        meeting_json = bbb_utils.xml_to_json(m_xml)

        # Now create a model for it.
        meeting, created = BBBRoom.objects.get_or_create(meeting_id=meeting_id, portal=current_portal)
        meeting.name = name
        meeting.meeting_id = meeting_json['meetingID']
        meeting.attendee_password = meeting_json['attendeePW']
        meeting.moderator_password = meeting_json['moderatorPW']
        meeting.internal_meeting_id = meeting_json['internalMeetingID']
        meeting.parent_meeting_id = meeting_json['parentMeetingID']
        meeting.voice_bridge = meeting_json['voiceBridge']
        meeting.dial_number = meeting_json['dialNumber']

        if not meeting_json:
            meeting.ended = True
        meeting.save()
        
        # set cached meeting api settings
        meeting._bbb_api = bbb_api
        return meeting
    
    def get_source_object(self):
        """ Attempts to find the source object for this BBBRoom, i.e. the
            Model instance with the media_tag attached that this BBBRoom is attached to.
            That instance should also have a CosinnusConferenceSettings attached. """
        event = self.event
        if event:
            return event
        raise ImproperlyConfigured("NYI: non-ConferenceEvent source types for BBBRooms are not yet supported!")
        return None
    
    def build_extra_create_parameters(self):
        """ Builds a parameter set for the create API call. Will use the inferred source 
            object that this BBBRoom belongs to to generate options. """
        return self._meta.model.build_extra_create_parameters_for_object(self.get_source_object())
    
    @classmethod
    def build_extra_create_parameters_for_object(cls, source_object):
        params = {}
        params.update(settings.BBB_DEFAULT_CREATE_PARAMETERS)
        params.update(settings.BBB_ROOM_TYPE_EXTRA_CREATE_PARAMETERS.get(source_object.get_bbb_room_type()))
        # special: the max_participants is currently finally derived from the source event
        max_participants = source_object.get_max_participants()
        if max_participants:
            params.update({
                'maxParticipants': max_participants,
            })
        return params
    
    def build_extra_join_parameters(self, user):
        """ Builds a parameter set fo the join API call for the join
            link for the user, from the default room parameters and the
            given room type's extra parameters """
        params = {}
        params.update(settings.BBB_DEFAULT_JOIN_PARAMETERS)
        params.update(settings.BBB_ROOM_TYPE_EXTRA_JOIN_PARAMETERS.get(self.room_type))
        if user.cosinnus_profile.avatar:
            domain = CosinnusPortal.get_current().get_domain()
            params.update({
                'avatarURL': domain + user.cosinnus_profile.get_avatar_thumbnail_url(size=(800,800))
            })
        return params
    
    def get_join_url(self, user):
        """ Returns the actual BBB-Server URL with tokens for a given user
            to join this room """
        password = self.get_password_for_user(user)
        display_name_func = settings.COSINNUS_CONFERENCES_USER_DISPLAY_NAME_FUNC
        if display_name_func is not None and callable(display_name_func):
            username = display_name_func(user)
        else:
            username = full_name(user)
        
        if self.meeting_id and password:
            extra_join_parameters = self.build_extra_join_parameters(user)
            return self.bbb_api.join_url(self.meeting_id, username, password, extra_parameter_dict=extra_join_parameters)
        return ''

    def get_absolute_url(self):
        """ Returns an on-portal-server URL that returns a redirect to the BBB-server URL """
        return reverse('cosinnus:bbb-room', kwargs={'room_id': self.id})

    def get_direct_room_url_for_user(self, user):
        """ Returns the direct BBB-server URL. This logic is also used by the 
            proxy-view used by `get_absolute_url`.
            This should be used as the boilerplate for the room-URL getter for a user,
            as it also handles creating statistics.
            @param request: (optional)  """
        if not self.check_user_can_enter_room(user):
            return None

        if not self.is_running:
            try:
                self.restart()
            except Exception as e:
                logger.exception(e)
        
        # add statistics visit
        try:
            room_event = self.event
            event_group = room_event and room_event.group or None
            BBBRoomVisitStatistics.create_user_visit_for_bbb_room(user, self, group=event_group)
        except Exception as e:
            if settings.DEBUG:
                raise
            logger.error('Error creating a statistic BBBRoom visit entry.', extra={'exception': e})
        
        return self.get_join_url(user)


class BBBRoomVisitStatistics(models.Model):
    """ This model represents a video/audio conference call with participants and/or presenters """
    
    bbb_room = models.ForeignKey('cosinnus.BBBRoom', verbose_name=_('BBB ROOM'), related_name='visits', 
        null=True, blank=True, on_delete=models.SET_NULL) 
    user = models.ForeignKey(User, verbose_name=_('Visitor'), related_name='bbb_room_visits', 
        null=True, blank=True, on_delete=models.SET_NULL)
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, verbose_name=_('Group'), related_name='+', 
        null=True, blank=True, on_delete=models.SET_NULL) 
    
    visit_datetime = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    
    # this field contains additional infos and backups of the stats that might be lost because
    # the related objects were deleted, EXCEPT any user info that has to honor the deletion!
    # attribute names are listed in `ALL_DATA_SETTINGS`
    data = PostgresJSONField(default=dict, blank=True, null=True)
    
    DATA_DATA_SETTING_ROOM_NAME = 'room_name'
    DATA_DATA_SETTING_GROUP_NAME = 'group_name'
    DATA_DATA_SETTING_GROUP_MANAGED_TAG_IDS = 'group_managed_tag_ids'
    DATA_DATA_SETTING_GROUP_MANAGED_TAG_SLUGS = 'group_managed_tag_slugs'
    DATA_DATA_SETTING_USER_MANAGED_TAG_IDS = 'group_managed_tag_ids'
    DATA_DATA_SETTING_USER_MANAGED_TAG_SLUGS = 'group_managed_tag_slugs'
    
    ALL_DATA_SETTINGS = [
        DATA_DATA_SETTING_ROOM_NAME,
        DATA_DATA_SETTING_GROUP_NAME,
        DATA_DATA_SETTING_GROUP_MANAGED_TAG_IDS,
        DATA_DATA_SETTING_GROUP_MANAGED_TAG_SLUGS,
        DATA_DATA_SETTING_USER_MANAGED_TAG_IDS,
        DATA_DATA_SETTING_USER_MANAGED_TAG_SLUGS,
    ]
    
    objects = models.Manager()
    
    def __str__(self):
        return f'<BBBRoomVisitStatistics for User: {self.user} and Room {self.bbb_room}'
    
    @classmethod
    def create_user_visit_for_bbb_room(cls, user, bbb_room, group=None):
        """ Helper function to create a visit statistic entry for when a user
            visits a room.
            Limits visits logging to no more than once per hour """
        if not bbb_room:
            return None
        if not user.is_authenticated:
            user = None
            
        # limit visit creation for (user, bbb_room) pairs to a time window
        a_short_time_ago = now() - timedelta(seconds=getattr(settings, 'BBB_ROOM_STATISTIC_VISIT_COOLDOWN_SECONDS', 60))
        recent_user_room_visits = cls.objects.filter(
            bbb_room=bbb_room,
            user=user,
            visit_datetime__gte=a_short_time_ago
        )
        if recent_user_room_visits.count() > 0:
            return None
        
        data = {
            cls.DATA_DATA_SETTING_ROOM_NAME: bbb_room.name,
        }
        if user:
            user_managed_tags = user.cosinnus_profile.get_managed_tags()
            if user_managed_tags:
                data.update({
                    cls.DATA_DATA_SETTING_USER_MANAGED_TAG_IDS: [tag.id for tag in user_managed_tags],
                    cls.DATA_DATA_SETTING_USER_MANAGED_TAG_SLUGS: [tag.slug for tag in user_managed_tags],
                })
        if group:
            data.update({
                cls.DATA_DATA_SETTING_GROUP_NAME: group.name,
            })
            group_managed_tags = group.get_managed_tags()
            if group_managed_tags:
                data.update({
                    cls.DATA_DATA_SETTING_GROUP_MANAGED_TAG_IDS: [tag.id for tag in group_managed_tags],
                    cls.DATA_DATA_SETTING_GROUP_MANAGED_TAG_SLUGS: [tag.slug for tag in group_managed_tags],
                })
        
        visit = BBBRoomVisitStatistics.objects.create(
            bbb_room=bbb_room,
            user=user,
            group=group,
            data=data,
        )
        return visit
        

def update_bbbroom_membership(sender, instance, signal, created, *args, **kwargs):
    rooms = BBBRoom.objects.filter(
        Q(attendees__id__in=[instance.user.id]) |
        Q(moderators__id__in=[instance.user.id]) |
        Q(group=instance.membership.group)
    )

    for room in rooms:
        room.join_user(instance.user)
