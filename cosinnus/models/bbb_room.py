import string
import random

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.translation import ugettext as _
from django.contrib.postgres.fields import JSONField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.urls.base import reverse
from django.conf import settings

from cosinnus.apis import bigbluebutton as bbb
from cosinnus.utils import bigbluebutton as bbb_utils
# from cosinnus.models import MEMBERSHIP_ADMIN
import logging
from django.core.cache import cache

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
    welcome_message = models.CharField(max_length=300, null=True, blank=True, verbose_name=_("the rooms welcome message"),
                                       help_text=_("the welcome message, that is displayed to attendees"))
    max_participants = models.PositiveIntegerField(blank=True, null=True, default=None, verbose_name="maximum number of users",
                                                   help_text="Maximum number in the conference at the same time. NOTE: Seems this needs to be +1 more the number that you actually want for BBB to allow!")
    dial_number = models.CharField(blank=True, null=True, default="", max_length=20,
                                   help_text=_("number for dialing into the conference via telephone"),
                                   verbose_name="telephone dial in number")
    voice_bridge = models.PositiveIntegerField(help_text=_("pin to enter for telephone participants"),
                                               verbose_name="dial in PIN", default=bbb_utils.random_voice_bridge,
                                               validators=[MinValueValidator(10000), MaxValueValidator(99999)])
    internal_meeting_id = models.CharField(max_length=100, blank=True, null=True)
    parent_meeting_id = models.CharField(max_length=100, blank=True, null=True)
    ended = models.BooleanField(default=False)
    options = JSONField(blank=True, null=True, default=dict, verbose_name="room options",
                        help_text=_("options for the room, that are represented in the bigbluebutton API"))

    objects = models.Manager()
    
    # cache key for each rooms participants
    PARTICIPANT_COUNT_CACHE_KEY = 'cosinnus/core/bbbroom/%d/participants' # bbb-room-id

    def __str__(self):
        return str(self.meeting_id)
    
    def save(self, *args, **kwargs):
        """ Assign current portal """
        created = bool(self.pk is None)
        if created and not self.portal:
            from cosinnus.models.group import CosinnusPortal
            self.portal = CosinnusPortal.get_current()
        super(BBBRoom, self).save(*args, **kwargs)

    def end(self):
        bbb.end_meeting(self.meeting_id, self.moderator_password)
        self.ended = True
        self.save()
    
    def retrieve_remote_user_count(self):
        """ Non-cached function to retrieve the remote user count for this meeting """
        try:
            meeting_info = bbb.meeting_info(self.meeting_id, self.moderator_password)
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

        if user in self.attendees.all():
            return self.attendee_password
        elif user in self.moderators.all():
            return self.moderator_password
        else:
            return ''

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
                meeting_info = bbb.meeting_info(self.meeting_id, self.attendee_password) 
                if meeting_info and meeting_info.get('running', False) == 'true':
                    return True
            except Exception as e:
                logger.exception(e)
        return False

    def restart(self):
        m_xml = bbb.start(
            name=self.name,
            meeting_id=self.meeting_id,
            welcome=self.welcome_message,
            attendee_password=self.attendee_password,
            moderator_password=self.moderator_password,
            voice_bridge=self.voice_bridge,
            max_participants=self.max_participants,
            options=self.options
        )

        meeting_json = bbb_utils.xml_to_json(m_xml)

        if not meeting_json:
            raise ValueError('Unable to restart meeting %s!' % self.meeting_id)

        if self.ended:
            self.ended = False
            self.save(update_fields=['ended'])

        return None

    @classmethod
    def create(cls, name, meeting_id, meeting_welcome='Welcome!', attendee_password=None,
               moderator_password=None, max_participants=None, voice_bridge=None, options=None):
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

        :param max_participants: Maximum number of participants moderator + attendees allowed at the same time
        :type: int

        :param voice_bridge: Dial in PIN for joining the meeting via telephone call
        :type: int range(10000 - 99999)

        :param options: Options for the BBBRoom according to the BBB API.
                         See https://docs.bigbluebutton.org/dev/api.html#create
        :type: dict
        """
        if attendee_password is None:
            attendee_password = bbb_utils.random_password()
        if moderator_password is None:
            moderator_password = bbb_utils.random_password()

        if options and type(options) is not dict:
            raise ValueError("Options parameter should be from type dict!")
        else:
            options = {}

        # default BBBRoom settings with given options
        default_options = settings.BBB_ROOM_DEFAULT_SETTINGS
        default_options.update(options)
        
        # monkeypatch for BBB appearently allowing one less persons to enter a room
        if max_participants is not None and settings.BBB_ROOM_FIX_PARTICIPANT_COUNT_PLUS_ONE:
            max_participants += 1
        
        m_xml = bbb.start(
            name=name,
            meeting_id=meeting_id,
            welcome=meeting_welcome,
            attendee_password=attendee_password,
            moderator_password=moderator_password,
            max_participants=max_participants,
            voice_bridge=voice_bridge,
            options=default_options
        )

        meeting_json = bbb_utils.xml_to_json(m_xml)

        from cosinnus.models.group import CosinnusPortal
        current_portal = CosinnusPortal.get_current()

        # Now create a model for it.
        meeting, created = BBBRoom.objects.get_or_create(meeting_id=meeting_id, portal=current_portal)
        meeting.name = name
        meeting.welcome_message = meeting_welcome
        meeting.meeting_id = meeting_json['meetingID']
        meeting.attendee_password = meeting_json['attendeePW']
        meeting.moderator_password = meeting_json['moderatorPW']
        meeting.internal_meeting_id = meeting_json['internalMeetingID']
        meeting.parent_meeting_id = meeting_json['parentMeetingID']
        meeting.voice_bridge = meeting_json['voiceBridge']
        meeting.dial_number = meeting_json['dialNumber']
        meeting.max_participants = max_participants
        meeting.options = default_options

        if not meeting_json:
            meeting.ended = True
        meeting.save()

        return meeting

    def get_absolute_url(self):
        return reverse('cosinnus:bbb-room', kwargs={'room_id': self.id})


def update_bbbroom_membership(sender, instance, signal, created, *args, **kwargs):
    rooms = BBBRoom.objects.filter(
        Q(attendees__id__in=[instance.user.id]) |
        Q(moderators__id__in=[instance.user.id]) |
        Q(group=instance.membership.group)
    )

    for room in rooms:
        room.join_user(instance.user)
