import logging
import random
import string
from urllib import request

from annoying.functions import get_object_or_None
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.test import RequestFactory
from django.template.defaultfilters import linebreaksbr
from django.urls.base import reverse
from django.utils import translation
from django.utils.translation import gettext as _

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
from cosinnus.utils.functions import clean_single_line_text
from django.template.defaultfilters import truncatechars
from cosinnus.models.membership import MANAGER_STATUS, MEMBER_STATUS
from cosinnus.models.conference import CosinnusConferenceSettings
from copy import copy
from cosinnus.utils.group import get_cosinnus_group_model
from builtins import issubclass
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_conference.utils import BBBGuestTokenAnonymousUser


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
    
    guest_token = models.CharField(max_length=100, null=True, blank=True, unique=True, editable=False,
                                   help_text='Token for guest access to this room via https://SERVER.COM/bbb/<token>')
    
    last_create_params = models.JSONField( verbose_name=_('Last create-call parameters'),
        blank=True, null=True, default=dict, editable=False, encoder=DjangoJSONEncoder,
        help_text="The parameters used for the last create call. Serves as a record only, new create params are derived from the source object's options!")
    
    
    objects = models.Manager()
    
    # cache key for each rooms participants
    PARTICIPANT_COUNT_CACHE_KEY = 'cosinnus/core/bbbroom/%d/participants' # bbb-room-id
    
    # the attr name on the User object that signifies the user is entering a bbb room via guest_token
    BBB_USER_GUEST_TOKEN_ATTR = 'bbb_guest_token'
    
    # the BigBlueButtonAPI instance for this room
    _bbb_api = None
    
    # the cached source object instance for this room
    _source_obj = '__unset__'

    def __str__(self):
        return str(self.meeting_id)
    
    @classmethod
    def clean_room_name(self, raw_name):
        """ Returns a clean, max-length version acceptable for the BBB create API """
        return truncatechars(clean_single_line_text(raw_name), 50)
    
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
        self.name = BBBRoom.clean_room_name(self.name)
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
            If the user object has a temporary bbb guest token attached that matches this room,
            attendee access is also given.
        Returns empty string, if user is no member of the room

        :return: password for the user to join the room
        :rtype: str
        """
        user_bbb_guest_token = getattr(user, self.BBB_USER_GUEST_TOKEN_ATTR, None)
        if check_user_superuser(user) or user in self.moderators.all():
            return self.moderator_password
        elif (user_bbb_guest_token and user_bbb_guest_token == self.guest_token) or user in self.attendees.all():
            return self.attendee_password
        else:
            return ''
    
    def check_user_can_enter_room(self, user):
        """ Checks if a user has the neccessary permissions to enter this room """
        return bool((user.is_authenticated or type(user) is BBBGuestTokenAnonymousUser) and self.get_password_for_user(user))

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
    
    def join_users(self, users, as_moderator=False):
        if as_moderator:
            self.moderators.add(*users)
            self.attendees.remove(*users)
        else:
            self.attendees.add(*users)
            self.moderators.remove(*users)

    def join_group_members(self, group):
        """ Automatically joins all members of the given group into the room,
            with priviledges depending on their membership status """
        for membership in group.memberships.all():
            if membership.status in MEMBER_STATUS:
                self.join_user(membership.user, as_moderator=bool(membership.status in MANAGER_STATUS))

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
    def is_recorded_meeting(self):
        """ Returns true if the options used for this meeting mean that the 
            video conference will be recorded in BBB """
        return self.last_create_params.get('record', None) == 'true'

    @property
    def source_object(self):
        """ Attempts to find the source object for this BBBRoom, i.e. the
            Model instance with the media_tag attached that this BBBRoom is attached to.
            That instance should also have a CosinnusConferenceSettings attached.
            Note: if other event types can carry BBBRooms, replace the `ConferenceEvent` here! """
        if self._source_obj == '__unset__':
            # try Conference Event
            from cosinnus_event.models import ConferenceEvent # noqa
            media_tag = self.tagged_objects.first()
            self._source_obj = get_object_or_None(ConferenceEvent, media_tag=media_tag)
            if self._source_obj:
                return self._source_obj
            
            # try Event
            from cosinnus_event.models import Event # noqa
            media_tag = self.tagged_objects.first()
            self._source_obj = get_object_or_None(Event, media_tag=media_tag)
            if self._source_obj:
                return self._source_obj
            
            # try Group
            from cosinnus.utils.group import get_cosinnus_group_model
            media_tag = self.tagged_objects.first()
            self._source_obj = get_object_or_None(get_cosinnus_group_model(), media_tag=media_tag)
            if self._source_obj:
                return self._source_obj
            
            if settings.DEBUG:
                raise ImproperlyConfigured("NYI: This bbb room source object type for BBBRooms is not yet supported!")
            self._source_obj = None
        return self._source_obj
    
    def restart(self):
        presentation_url = None
        source_obj = self.source_object
        if source_obj:
            presentation_url = source_obj.get_presentation_url()
        
        create_params = self.build_extra_create_parameters()
        
        # BBB guest access: append the `moderatorOnlyMessage` param by this BBB room's guest_token URL, if the message param exists
        guest_token = self.get_guest_token()
        create_params = self.__class__.add_guest_link_moderator_only_message_to_params(create_params, guest_token)
            
        m_xml = self.bbb_api.start(
            name=self.name,
            meeting_id=self.meeting_id,
            attendee_password=self.attendee_password,
            moderator_password=self.moderator_password,
            voice_bridge=self.voice_bridge,
            options=create_params,
            presentation_url=presentation_url,
        )

        meeting_json = bbb_utils.xml_to_json(m_xml)

        if not meeting_json:
            raise ValueError('Unable to restart meeting %s!' % self.meeting_id)
        
        self.last_create_params = create_params
        self.ended = False
        self.save()

    @classmethod
    def create(cls, name, meeting_id, attendee_password=None,
               moderator_password=None, voice_bridge=None,
               presentation_url=None, source_object=None):
        """ Creates a new BBBRoom and crete a room on the remote bbb-server.

        :param name: Name of the BBBRoom
        :type: str

        :param meeting_id: ID on the BBB-Server. Must be unique for any meeting running on the BBB-Server
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
        name = cls.clean_room_name(name)
        
        if attendee_password is None:
            attendee_password = bbb_utils.random_password()
        if moderator_password is None:
            moderator_password = bbb_utils.random_password()

        bbb_api = BigBlueButtonAPI(source_object=source_object)
        create_params = cls.build_extra_create_parameters_for_object(source_object, meeting_id=meeting_id, meeting_name=name)
        
        # BBB guest access: append the `moderatorOnlyMessage` param by this BBB room's guest_token URL, if the message param exists
        guest_token = cls._generate_guest_token(source_object)
        create_params = cls.add_guest_link_moderator_only_message_to_params(create_params, guest_token)
        
        m_xml = bbb_api.start(
            name=name,
            meeting_id=meeting_id,
            attendee_password=attendee_password,
            moderator_password=moderator_password,
            voice_bridge=voice_bridge,
            options=create_params,
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
        meeting.last_create_params = create_params
        meeting.guest_token = guest_token

        if not meeting_json:
            meeting.ended = True
        meeting.save()
        
        # set cached meeting api settings
        meeting._bbb_api = bbb_api
        return meeting
    
    def build_extra_create_parameters(self):
        """ Builds a parameter set for the create API call. Will use the inferred source 
            object that this BBBRoom belongs to to generate options. """
        return self._meta.model.build_extra_create_parameters_for_object(self.source_object,  meeting_id=self.meeting_id, meeting_name=self.name)
    
    @classmethod
    def build_extra_create_parameters_for_object(cls, source_object, meeting_id=None, meeting_name=None):
        params = {}
        params.update(settings.BBB_DEFAULT_CREATE_PARAMETERS)
        # add the source object's options from all inherited settings objects
        params.update(cls._get_bbb_extra_params_for_api_call('create', source_object))
        # special: the max_participants is currently finally derived from the source event
        max_participants = source_object.get_max_participants() # see `BBBRoomMixin.get_max_participants`
        if max_participants:
            params.update({
                'maxParticipants': max_participants,
            })
            
        # collect meta-tags for the BBB create call. these free-form parameters
        # can be used to save arbitrary information for a BBB-meeting and are 
        # used to retrieve recorded meetings later on
        group = None
        if hasattr(source_object, 'group'):
            group = source_object.group
        elif type(source_object) is get_cosinnus_group_model() or issubclass(source_object.__class__, get_cosinnus_group_model()):
            group = source_object
        portal_slug = CosinnusPortal.get_current().slug
        if group:
            params.update({
                'meta_we-portal-group-id': f'{portal_slug}-{group.id}',
                'meta_we-group-id': group.id,
                'meta_we-group-slug': group.slug,
                'meta_we-group-name': group.name,
            })
        params.update({
            'meta_we-portal': portal_slug,
            'meta_we-meeting-id': meeting_id,
            'meta_we-meeting-name': meeting_name,
            'meta_we-portal-source-object': f'{portal_slug}-{source_object._meta.model_name}-{source_object.id}'
        })
        return params
    
    def build_extra_join_parameters(self, user):
        """ Builds a parameter set fo the join API call for the join
            link for the user, from the default room parameters and the
            given room type's extra parameters """
        params = {}
        # add the source object's options from all inherited settings objects
        params.update(self._meta.model._get_bbb_extra_params_for_api_call('join', self.source_object))
        # add the user's avatar from their profile
        profile = getattr(user, 'cosinnus_profile', None)
        if profile and profile.avatar:
            domain = CosinnusPortal.get_current().get_domain()
            params.update({
                'avatarURL': domain + profile.get_avatar_thumbnail_url(size=(800,800))
            })
        if profile and profile.language:
            cur_language = translation.get_language()
            params.update({
                'userdata-bbb_override_default_locale': cur_language
            })
        return params
    
    @classmethod
    def _get_bbb_extra_params_for_api_call(cls, api_call_method, source_object):
        """ Collect all BBB extra params for a specific api call method,
            as set by the collected inherited CosinnusConferenceSettings
            for the `source_object` and all of its ancestors in the settings inheritance chain.
            @param api_call_method: the BBB API-method, such as 'create' or 'join'. this determines,
                which params are selected from the configured `settings.BBB_PRESET_FORM_FIELD_PARAMS`
                for each field_name in the settings presets
            @param source_object: the source object from which the inheritance chain starts """
        # add the source object's options from all inherited settings objects
        conference_settings = CosinnusConferenceSettings.get_for_object(source_object)
        # this is the merged params object containing the flattened hierarchy of inherited objects
        bbb_params = conference_settings.get_finalized_bbb_params()
        call_params = bbb_params.get(api_call_method, {})
        # block "premium only" params for non-premium source obejcts 
        # by resetting their call values to the portal default ones
        source_group = source_object.get_group_for_bbb_room()
        if not source_group.is_premium_ever:
            for premium_preset_name in settings.BBB_PRESET_USER_FORM_FIELDS_PREMIUM_ONLY:
                preset_call_param_dict = list(settings.BBB_PRESET_FORM_FIELD_PARAMS.get(premium_preset_name, {}).values())[0].get(api_call_method, {})
                for blocked_param_name in preset_call_param_dict.keys():
                    portal_default_value = settings.BBB_PARAM_PORTAL_DEFAULTS.get(api_call_method, {}).get(blocked_param_name)
                    call_params[blocked_param_name] = portal_default_value
        # Convert newlines in text parameters to html
        for __, text_param in settings.BBB_PRESET_FORM_FIELD_TEXT_PARAMS.values():
            if text_param in call_params:
                call_params[text_param] = linebreaksbr(call_params[text_param].strip())
        return call_params
    
    @classmethod
    def add_guest_link_moderator_only_message_to_params(cls, params, guest_token=None):
        """ Adds a moderator message with a guest invite link to the create/join parameters of a BBB call """
        if guest_token:
            message = params.get('moderatorOnlyMessage', '').strip()
            if message:
                message += ' '
            guest_link_text = settings.BBB_MODERATOR_MESSAGE_GUEST_LINK_TEXT
            guest_url = group_aware_reverse('cosinnus:bbb-room-guest-access', kwargs={'guest_token': guest_token})
            params['moderatorOnlyMessage'] = f'{message}{guest_link_text} <a href="{guest_url}" target="_blank">{guest_url}</a>'
        return params
    
    def get_join_url(self, user):
        """ Returns the actual BBB-Server URL with tokens for a given user
            to join this room """
        password = self.get_password_for_user(user)
        username = 'Unnamed User'
        if type(user) is BBBGuestTokenAnonymousUser:
            username = user.bbb_user_name
        else:
            display_name_func = settings.COSINNUS_CONFERENCES_USER_DISPLAY_NAME_FUNC
            if display_name_func is not None and callable(display_name_func):
                username = display_name_func(user)
            else:
                username = full_name(user)
        
        if self.meeting_id and password:
            extra_join_parameters = self.build_extra_join_parameters(user)
            # if the user is joining via a guest link, set the password to empty string and add `guest=true` to params
            user_bbb_guest_token = getattr(user, self.BBB_USER_GUEST_TOKEN_ATTR, None)
            user_is_portal_guest = bool(user.is_authenticated and user.is_guest)
            if (user_bbb_guest_token and user_bbb_guest_token == self.guest_token) or user_is_portal_guest:
                extra_join_parameters.update({
                    'guest': 'true',
                })
            return self.bbb_api.join_url(self.meeting_id, username, password, extra_parameter_dict=extra_join_parameters)
        return ''
    
    @classmethod
    def _generate_guest_token(cls, source_obj=None, max_tries=10):
        """ Generate a token for `get_guest_token()` """
        # create a 3-letter part from the slug of the source objects group/conference
        slug_part = None
        if source_obj:
            # try Group
            if type(source_obj) is get_cosinnus_group_model() or issubclass(source_obj.__class__, get_cosinnus_group_model()):
                slug_part = source_obj.slug
            elif getattr(source_obj, 'group', None):
                slug_part = source_obj.group.slug
        if slug_part:
            slug_part = slug_part.replace('-', '').replace('_', '').lower().ljust(3, 'x')[:3]
        if not slug_part:
            slug_part = 'bbb'
        
        random_string = get_random_string(9, allowed_chars='abcdefghijklmnopqrstuvwxyz0123456789')
        new_token = f'{slug_part}-{random_string[:3]}-{random_string[3:6]}-{random_string[6:9]}'
        # check for duplicate tokens
        if BBBRoom.objects.filter(guest_token__iexact=new_token).count() > 0:
            if max_tries <= 0:
                return None
            return cls._generate_guest_token(source_obj, max_tries=max_tries-1)
        return new_token
    
    def get_guest_token(self):
        """ Will generate a unique guest token to use with url 'cosinnus:bbb-guest-room-access' for this room
            if one doesn't exist and return it.
            Tokens will be generated in the form "sss-xxx-xxx-xxx" where "sss" are the first 3 alphanumeric letters of
            the conference slug and "xxx" are random alphanumeric chars. """
        if not self.guest_token:
            try:
                new_token = self.__class__._generate_guest_token(self.source_object)
                if new_token is None:
                    return None
                self.guest_token = new_token
                self.save(update_fields=['guest_token'])
            except Exception as e:
                logger.warning('BBB: Error trying to generate a guest token for BBB room.', extra={'bbb-room-id': self.id, 'exception': str(e)})
                self.guest_token = None
        return self.guest_token

    def get_absolute_url(self):
        """ Returns an on-portal-server URL that returns a redirect to the BBB-server URL """
        return reverse('cosinnus:bbb-room', kwargs={'room_id': self.id})
    
    def get_admin_change_url(self):
        """ Returns the django admin edit page for this object. """
        return reverse('admin:cosinnus_bbbroom_change', kwargs={'object_id': self.id})
    
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
            source_obj = self.source_object
            if source_obj and user.is_authenticated:
                BBBRoomVisitStatistics.create_user_visit_for_bbb_room(user, self, group=source_obj.get_group_for_bbb_room())
        except Exception as e:
            if settings.DEBUG:
                raise
            logger.error('Error creating a statistic BBBRoom visit entry.', extra={'exception': e})
        
        return self.get_join_url(user)

    def get_invitation_text(self, platform_join_url=None):
        """ Returns an invitation text to the BBB room containing join URL and dial-in information.
        @param platform_join_url: Can contain the absolute URL of the object wth the conference (i.e. group, event).
            If passed this URL is used in the invitation text, otherwise the BBB guest access URL is used.
        """
        invitation = _('Join "%(name)s"!') % {'name': self.name}

        if platform_join_url:
            join_url = platform_join_url
        else:
            guest_token = self.get_guest_token()
            join_url = group_aware_reverse('cosinnus:bbb-room-guest-access', kwargs={'guest_token': guest_token})
        invitation += '\n\n' + _('To join the conference in the browser visit %(url)s.') % {'url': join_url}

        if self.dial_number and self.voice_bridge:
            invitation += '\n\n' + _(
                'To join the conference by phone dial "%(number)s" and enter the following PIN: "%(pin)s#". '
                'Use the 0-key on your phone to toggle mute on/off.'
            ) % {'number': self.dial_number, 'pin': self.voice_bridge}

        return invitation

    def get_invitation_alert_text(self):
        """ Returns the text shown in the invitation alert. """
        return _('Invitation copied to clipboard.')


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
    data = models.JSONField(default=dict, encoder=DjangoJSONEncoder, blank=True, null=True)
    
    DATA_DATA_SETTING_ROOM_NAME = 'room_name'
    DATA_DATA_SETTING_ROOM_SOURCE_TYPE = 'room_source_type'
    DATA_DATA_SETTING_GROUP_NAME = 'group_name'
    DATA_DATA_SETTING_GROUP_SLUG = 'group_slug'
    DATA_DATA_SETTING_GROUP_MANAGED_TAG_IDS = 'group_managed_tag_ids'
    DATA_DATA_SETTING_GROUP_MANAGED_TAG_SLUGS = 'group_managed_tag_slugs'
    DATA_DATA_SETTING_USER_MANAGED_TAG_IDS = 'group_managed_tag_ids'
    DATA_DATA_SETTING_USER_MANAGED_TAG_SLUGS = 'group_managed_tag_slugs'
    
    ALL_DATA_SETTINGS = [
        DATA_DATA_SETTING_ROOM_NAME,
        DATA_DATA_SETTING_ROOM_SOURCE_TYPE,
        DATA_DATA_SETTING_GROUP_NAME,
        DATA_DATA_SETTING_GROUP_SLUG,
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
        # get the name of the type of the source object the bbb room is in
        src_obj = bbb_room.source_object
        src_name = type(src_obj).__name__ # safe even for NoneType
        data.update({
            cls.DATA_DATA_SETTING_ROOM_SOURCE_TYPE: src_name,
        })
        
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
                cls.DATA_DATA_SETTING_GROUP_SLUG: group.slug,
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
