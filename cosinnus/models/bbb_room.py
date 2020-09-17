import string
import random

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.contrib.postgres.fields import JSONField

from cosinnus.apis import bigbluebutton as bbb
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.urls.base import reverse
# from cosinnus.models.group import CosinnusGroup
# from cosinnus.models import MEMBERSHIP_ADMIN


def random_meeting_id():
    """ generates a random meeting_id to identify the meeting at BigBlueButton """
    return "room-" + random_password()


def random_password(length=5):
    """ generates a random moderator password for a BBBRoom  with lowercase ASCII characters """
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


def random_voice_bridge():
    """ generates a random voice bridge dial in PIN between 10000 and 99999 that is unique within all BBB-Rooms

    :return: random integer in the range of 10000 - 99999
    :rtype: int
    """
    existing_pins = list(BBBRoom.objects.filter(ended=False).values_list("dial_number", flat=True))

    random_pin = 10000

    while True:
        random_pin = random.randint(10000, 99999)
        if random_pin not in existing_pins:
            break

    return random_pin


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
    meeting_id = models.CharField(max_length=200, null=True, blank=True)
    name = models.CharField(max_length=160, null=True, blank=True, verbose_name=_("room name or title"))
    moderator_password = models.CharField(max_length=30, default=random_password,
                                          help_text=_("the password set to enter the room as a moderator"))
    attendee_password = models.CharField(max_length=30, default='', null=True, blank=True,
                                         help_text=_("the password set to enter the room as a attendee"))
    welcome_message = models.CharField(max_length=300, null=True, blank=True, verbose_name=_("the rooms welcome message"),
                                       help_text=_("the welcome message, that is displayed to attendees"))
    max_participants = models.PositiveIntegerField(null=True, default=None, verbose_name="maximum number of users",
                                                   help_text=_("maximum number in the conference at the same time"))
    dial_number = models.CharField(blank=True, null=True, default="", max_length=20,
                                   help_text=_("number for dialing into the conference via telephone"),
                                   verbose_name="telephone dial in number")
    voice_bridge = models.PositiveIntegerField(help_text=_("pin to enter for telephone participants"),
                                               unique=True, verbose_name="dial in PIN", default=random_voice_bridge,
                                               validators=[MinValueValidator(10000), MaxValueValidator(99999)])
    internal_meeting_id = models.CharField(max_length=100, blank=True, null=True)
    parent_meeting_id = models.CharField(max_length=100, blank=True, null=True)
    ended = models.BooleanField(default=False)
    options = JSONField(blank=True, null=True, default=dict, verbose_name="room options",
                        help_text=_("options for the room, that are represented in the bigbluebutton API"))

    objects = models.Manager()

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

    def join_user(self, user, membership_status_int):
        if membership_status_int == 2:
            # TODO fix this to reference to MEMBERSHIP_ADMIN
            self.moderators.add(user)
            self.attendees.remove(user)
        elif membership_status_int == 1:
            self.attendees.add(user)
            self.moderators.remove(user)

    def join_group_members(self, group):
        for membership in group.memberships.all():
            self.join_user(membership.user, membership.status)

    @property
    def members(self):
        return self.moderators.all() | self.attendees.all()

    def restart(self):
        m_xml = bbb.start(
            name=self.name,
            meeting_id=self.meeting_id,
            welcome=self.welcome_message,
            attendee_password=self.attendee_password,
            moderator_password=self.moderator_password
        )

        meeting_json = bbb.xml_to_json(m_xml)

        if meeting_json['returncode'] != 'SUCCESS':
            raise ValueError('Unable to create meeting!')

        return None

    @classmethod
    def create(cls, name, meeting_id, meeting_welcome='Welcome!', attendee_password=None,
               moderator_password=None, max_participants=None, voice_bridge=None):
        if attendee_password is None:
            attendee_password = random_password()
        if moderator_password is None:
            moderator_password = random_password()

        if max_participants or voice_bridge:
            m_xml = bbb.start_verbose(
                name=name,
                meeting_id=meeting_id,
                welcome=meeting_welcome,
                attendee_password=attendee_password,
                moderator_password=moderator_password
            )

        else:
            m_xml = bbb.start(
                name=name,
                meeting_id=meeting_id,
                welcome=meeting_welcome,
                attendee_password=attendee_password,
                moderator_password=moderator_password
            )

        meeting_json = bbb.xml_to_json(m_xml)

        if meeting_json['returncode'] != 'SUCCESS':
            raise ValueError('Unable to create meeting!')

        # Now create a model for it.
        meeting, _ = BBBRoom.objects.get_or_create(meeting_id=meeting_id)
        meeting.name = name
        meeting.welcome_message = meeting_welcome
        meeting.meeting_id = meeting_json['meetingID']
        meeting.attendee_password = meeting_json['attendeePW']
        meeting.moderator_password = meeting_json['moderatorPW']
        meeting.internal_meeting_id = meeting_json['internalMeetingID']
        meeting.parent_meeting_id = meeting_json['parentMeetingID']
        meeting.voice_bridge = meeting_json['voiceBridge']
        meeting.dial_number = meeting_json['dialNumber']
        meeting.save()

        return meeting
    
    def get_absolute_url(self):
        return reverse('cosinnus:bbb-room', kwargs={'room_id': self.id})
    