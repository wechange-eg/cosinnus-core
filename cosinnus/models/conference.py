# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import locale
import logging

from annoying.functions import get_object_or_None
from django.contrib.contenttypes.fields import GenericForeignKey, \
    GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField as PostgresJSONField
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from phonenumber_field.modelfields import PhoneNumberField
import six

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.tagged import get_tag_object_model
from cosinnus.models.mixins.translations import TranslateableFieldsModelMixin
from cosinnus.utils.files import get_conference_conditions_filename
from cosinnus.utils.functions import clean_single_line_text, \
    unique_aware_slugify
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.views.mixins.group import ModelInheritsGroupReadWritePermissionsMixin


logger = logging.getLogger('cosinnus')


def get_parent_object_in_conference_setting_chain(source_object):
    """ Will traverse upwards one step in the conference-setting hierarchy chain for the given object
        and return that higher-level object. 
    
        The hierarchy chain is:
        - cosinnus.BBBRoom
        - cosinnus_event.ConferenceEvent 
        - cosinnus.CosinnusConferenceRoom
        - cosinnus.CosinnusGroup
        - cosinnus.CosinnusPortal 
        
        @param return: None if it arrived at CosinnusPortal or was given None. Else, the higher object in the chain. """ 
        
    if source_object is None:
        return None
    try:
        from cosinnus_event.models import ConferenceEvent # noqa
    except ImportError:
        ConferenceEvent = None
    from cosinnus.models.bbb_room import BBBRoom
                    
    # BBBRoom --> tagged object for this room if there is one
    if type(source_object) is BBBRoom and ConferenceEvent is not None:
        conference_event = get_object_or_None(ConferenceEvent, media_tag__bbb_room=source_object)
        return conference_event
    # ConferenceEvent --> CosinnusConferenceRoom
    if ConferenceEvent is not None and type(source_object) is ConferenceEvent:
        return source_object.room
    # ConferenceRoom --> CosinnusGroup
    if type(source_object) is CosinnusConferenceRoom:
        return source_object.group
    # CoinnusGroup --> CosinnusPortal
    if type(source_object) is get_cosinnus_group_model() or issubclass(source_object.__class__, get_cosinnus_group_model()):
        return source_object.portal
    # else: return None
    return None


class CosinnusConferenceSettings(models.Model):
    """ A BBB settings container able to be attached to various objects to provide
        a granular hierarchy on settings. 
        Each level in the chain of the hierarchy for a BBBRoom object will be
        checked for this settings object, and if not found, the next higher level
        settings will be inherited. """
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    
    bbb_server_choice = models.PositiveSmallIntegerField(_('BBB Server'), blank=False,
        default=0, choices=settings.COSINNUS_BBB_SERVER_CHOICES,
        help_text='The default chosen BBB-Server/Cluster setting for the generic object. WARNING: changing this will cause new meeting connections to use the new server, even for ongoing meetings on the old server, essentially splitting a running meeting in two!')
    bbb_server_choice_premium = models.PositiveSmallIntegerField(_('BBB Server for Premium Conferences'), blank=False,
        default=0, choices=settings.COSINNUS_BBB_SERVER_CHOICES,
        help_text='The chosen BBB-Server/Cluster setting for the generic object, that will be used when the group of that object is currently in its premium state. WARNING: changing this will cause new meeting connections to use the new server, even for ongoing meetings on the old server, essentially splitting a running meeting in two!')
    
    CACHE_KEY = 'cosinnus/core/conferencesetting/class/%s/id/%d'
    
    class Meta(object):
        app_label = 'cosinnus'
        verbose_name = _('Cosinnus Conference Setting')
        verbose_name_plural = _('Cosinnus Conference Settings')
        unique_together = (('content_type', 'object_id',),)
    
    @classmethod
    def get_for_object(cls, source_object=None, no_traversal=False):
        """ Given any object in the BBB settings hierarchy chain,
            checks if there is a settings object attached and returns it,
            or checks the next higher object in the chain.
            If arrived at CosinnusPortal, and no setings object is found,
            None is returned.
            
            The currently supported source_object attachment points for CosinnusConferenceSettings are, 
            in order of the hierarchy chain (see ``).
            
            Furthermore, this function will accept these models as source_object 
            and use the resolved cosinnus_event.ConferenceEvent as chain starting point, if there is one:
                - cosinnus.BBBRoom 
            
            @param source_object: Any object. If it matches a model valid for the chain, we check the chain.
                                    If None is supplied, the portal default settings will be returned.
            @param no_traversal: if True, will only attempt to find a setting object on the `source_object`
                                    and not recursively check its parents
            .
        """
        # if no object is given, use the portal as default
        obj = source_object or CosinnusPortal.get_current()
        
        cache_key = cls.CACHE_KEY % (obj.__class__.__name__, obj.id)
        setting_obj = cache.get(cache_key)
        if not setting_obj:
            # can't be Falsy because None is a valid return value
            setting_obj = 'UNSET'
            
            # find and return conference settings if attached to our current object
            conference_settings = None
            try:
                conference_settings = obj.conference_settings_assignments.all()[0]
            except:
                pass
            if conference_settings:
                setting_obj = conference_settings
            
            # CosinnusPortal --> (End of chain because the portal had no settings, and settings seem to be configured anywhere)
            if setting_obj == 'UNSET' and (no_traversal or source_object is None or type(obj) is CosinnusPortal):
                setting_obj = None
            
            if setting_obj == 'UNSET':
                # no settings found; check next object in chain:
                parent_object = get_parent_object_in_conference_setting_chain(obj)
                setting_obj = cls.get_for_object(parent_object)
                
            cache.set(cache_key, setting_obj, settings.COSINNUS_CONFERENCE_SETTING_MICRO_CACHE_TIMEOUT)
        
        return setting_obj
        
    
    @property
    def bbb_server_choice_text(self):
        return settings.COSINNUS_BBB_SERVER_CHOICES[self.bbb_server_choice][1]
    
    @property
    def bbb_server_choice_premium_text(self):
        return settings.COSINNUS_BBB_SERVER_CHOICES[self.bbb_server_choice_premium][1]
    

class CosinnusConferenceRoomQS(models.query.QuerySet):

    def visible(self):
        """ Filters for visible Rooms """
        return self.filter(is_visible=True)


class CosinnusConferenceRoomManager(models.Manager):
    
    def all_in_portal(self):
        """ Returns all groups within the current portal only """
        return self.active().filter(portal=CosinnusPortal.get_current())
    
    def visible(self):
        """ Returns visible Rooms """
        qs = self.get_queryset()
        return qs.filter(is_visible=True)
    
    def get_queryset(self):
        return CosinnusConferenceRoomQS(self.model, using=self._db)\
                .select_related('group').order_by('sort_index', 'title')
    

@python_2_unicode_compatible
class CosinnusConferenceRoom(TranslateableFieldsModelMixin,
                             ModelInheritsGroupReadWritePermissionsMixin,
                             models.Model):
    """ A model for rooms inside a conference group object.
        Each room will be displayed as a list in the conference main page
        and can be displayed in different ways, depending on its type """
    
    TYPE_LOBBY = 0
    TYPE_STAGE = 1
    TYPE_WORKSHOPS = 2
    TYPE_DISCUSSIONS = 3
    TYPE_COFFEE_TABLES = 4
    TYPE_RESULTS = 5
    TYPE_PARTICIPANTS = 6
    
    TYPE_CHOICES = (
        (TYPE_LOBBY, _('Lobby')),
        (TYPE_STAGE, _('Stage')),
        (TYPE_WORKSHOPS, _('Workshops')),
        (TYPE_DISCUSSIONS, _('Discussions')),
        (TYPE_COFFEE_TABLES, _('Coffee Tables')),
        (TYPE_RESULTS, _('Results')),
        (TYPE_PARTICIPANTS, _('Participants')),
    )
    
    # rooms of these types will initialize a corresponding rocketchat room
    ROCKETCHAT_ROOM_TYPES = (
        TYPE_LOBBY,
        TYPE_STAGE,
        TYPE_WORKSHOPS,
        TYPE_DISCUSSIONS,
        TYPE_COFFEE_TABLES,
    )
    
    translateable_fields = ['title', 'description']
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, verbose_name=_('Team'),
        related_name='rooms', on_delete=models.CASCADE)

    title = models.CharField(_('Title'), max_length=250) # removed validators=[group_name_validator])
    slug = models.SlugField(_('Slug'), 
        help_text=_('Be extremely careful when changing this slug manually! There can be many side-effects (redirects breaking e.g.)!'), 
        max_length=50)
    description = models.TextField(verbose_name=_('Short Description'),
         blank=True)
    
    # may not be changed after creation!
    type = models.PositiveSmallIntegerField(_('Conference Room Type'), blank=False,
        default=TYPE_LOBBY, choices=TYPE_CHOICES)
    
    is_visible = models.BooleanField(_('Is visible'),
        help_text='If a room is not visible, it is not shown in any room lists',
        default=True)
    sort_index = models.PositiveSmallIntegerField(_('Sorting index'),
        help_text='Rooms are ordered in ascending order on this field',
        default=1)
    
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Creator'),
        on_delete=models.CASCADE,
        null=True,
        related_name='rooms')
    last_modified = models.DateTimeField(
        verbose_name=_('Last modified'),
        editable=False,
        auto_now=True)
    
    # connected rocketchat room to this room. 
    # only initialized for some room types 
    rocket_chat_room_id = models.CharField(_('RocketChat room id'), max_length=250, null=True, blank=True)
    rocket_chat_room_name = models.CharField(_('RocketChat room name'), max_length=250, null=True, blank=True,
            help_text='The verbose room name for linking URLs')

    # flag to enable/disable rocket chat
    show_chat = models.BooleanField(_('Show chat'),
        help_text='Show rocket chat in sidebar',
        default=True)

    # Type: CoffeeTable field only
    allow_user_table_creation = models.BooleanField(_('Allow users to create new coffee tables'),
        help_text='Otherwise, only organisers can create new tables',
        default=settings.COSINNUS_CONFERENCE_COFFEETABLES_ALLOW_USER_CREATION_DEFAULT)
    # Type: CoffeeTable field only
    max_coffeetable_participants = models.PositiveSmallIntegerField(_('Maximum Coffee Table Participants'),
        blank=False, default=settings.COSINNUS_CONFERENCE_COFFEETABLES_MAX_PARTICIPANTS_DEFAULT,
        validators=[MinValueValidator(2), MaxValueValidator(512)])
    
    # Type: Results field only
    target_result_group = models.OneToOneField(settings.COSINNUS_GROUP_OBJECT_MODEL, 
        verbose_name=_('Result Project'), related_name='conference_room',
        null=True, blank=True, on_delete=models.SET_NULL)
    
    conference_settings_assignments = GenericRelation('cosinnus.CosinnusConferenceSettings')
    
    objects = CosinnusConferenceRoomManager()
    
    
    class Meta(object):
        ordering = ('sort_index', 'title')
        verbose_name = _('Conference Room')
        verbose_name_plural = _('Conference Rooms')
        unique_together = ('slug', 'group', )

    def __init__(self, *args, **kwargs):
        super(CosinnusConferenceRoom, self).__init__(*args, **kwargs)

    def __str__(self):
        return 'Conference Room %s (Group %s)' % (self.title, self.group.slug)
    
    def save(self, *args, **kwargs):
        created = bool(self.pk is None)
        slugs = [self.slug] if self.slug else []
        self.title = clean_single_line_text(self.title)
        
        unique_aware_slugify(self, 'title', 'slug', group_id=self.group_id)
        
        if not self.slug:
            raise ValidationError(_('Slug must not be empty.'))
        slugs.append(self.slug)
        
        super(CosinnusConferenceRoom, self).save(*args, **kwargs)
        
        # initialize/sync room-type-specific extras
        self.ensure_room_type_dependencies()
        
    def get_absolute_url(self):
        return group_aware_reverse('cosinnus:conference:room', kwargs={'group': self.group, 'slug': self.slug})
    
    def get_maintenance_url(self):
        return group_aware_reverse('cosinnus:conference:page-maintenance-room', kwargs={'group': self.group, 'slug': self.slug})
    
    def get_edit_url(self):
        return group_aware_reverse('cosinnus:conference:room-edit', kwargs={'group': self.group, 'slug': self.slug})
    
    def get_delete_url(self):
        return group_aware_reverse('cosinnus:conference:room-delete', kwargs={'group': self.group, 'slug': self.slug})
    
    def get_room_create_url(self):
        return group_aware_reverse('cosinnus:event:conference-event-add', kwargs={'group': self.group, 'room_slug': self.slug})
    
    def get_rocketchat_room_url(self):
        if not settings.COSINNUS_ROCKET_ENABLED or not self.type in self.ROCKETCHAT_ROOM_TYPES \
                or settings.COSINNUS_CONFERENCES_USE_COMPACT_MODE:
            return ''
        if not self.rocket_chat_room_id or not self.rocket_chat_room_name:
            self.ensure_room_type_dependencies()
        if not self.rocket_chat_room_id or not self.rocket_chat_room_name:
            return ''
        room_id = self.rocket_chat_room_name
        return f'{settings.COSINNUS_CHAT_BASE_URL}/group/{room_id}/?layout=embedded'
    
    def ensure_room_type_dependencies(self):
        """ Depending on a room type, initialize different extras like rocketchat rooms """
        if settings.COSINNUS_ROCKET_ENABLED and self.type in self.ROCKETCHAT_ROOM_TYPES \
                and not settings.COSINNUS_CONFERENCES_USE_COMPACT_MODE:
            self.sync_rocketchat_room()
    
    def sync_rocketchat_room(self, force=False):
        """ Can be safely called with force=False without re-creating rooms """
        if settings.COSINNUS_ROCKET_ENABLED and self.type in self.ROCKETCHAT_ROOM_TYPES \
                and not settings.COSINNUS_CONFERENCES_USE_COMPACT_MODE:
            if not self.rocket_chat_room_id or force:
                from cosinnus_message.rocket_chat import RocketChatConnection
                rocket = RocketChatConnection()
                room_name = f'{self.slug}-{self.group.slug}-{get_random_string(7)}'
                internal_room_id = rocket.create_private_room(room_name, self.creator, 
                      member_users=self.group.actual_members, additional_admin_users=self.group.actual_admins)
                if internal_room_id:
                    self.rocket_chat_room_id = internal_room_id
                    self.rocket_chat_room_name = room_name
                    self.save()
                else:
                    logger.error('Could not create a conferenceroom rocketchat room!', 
                                 extra={'conference-room-id': self.id, 'conference-room-slug': self.slug})
    @property
    def non_table_events_qs(self):
        from cosinnus_event.models import ConferenceEvent # noqa
        return self.events.filter(is_break=False)\
                .exclude(type=ConferenceEvent.TYPE_COFFEE_TABLE)\
                .order_by('from_date')


class ParticipationManagement(models.Model):
    """ A settings object for a CosinnusConference that determines how and when 
        CosinnusConferenceApplications may be submitted, as well as other meta options
        for the application options for that conference. """

    participants_limit = models.IntegerField(blank=True, null=True)
    application_start = models.DateTimeField(blank=True, null=True)
    application_end = models.DateTimeField(blank=True, null=True)
    application_conditions = models.TextField(blank=True)
    application_conditions_upload = models.FileField(_("Conditiions for participation"),
                                  help_text=_('Shown as a download link near the checkbox to accept the conditions.'),
                                  null=True, blank=True,
                                  upload_to=get_conference_conditions_filename,
                                  max_length=250)
    application_options = PostgresJSONField(default=list, blank=True, null=True)
    conference = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL,
                                           verbose_name=_('Participation Management'),
                                           related_name='participation_management',
                                           on_delete=models.CASCADE)
    
    information_field_enabled = models.BooleanField(_('Request user information'), default=True)
    information_field_initial_text = models.TextField(_('Pre-filled content for the information field'), blank=True, null=True)
    
    priority_choice_enabled = models.BooleanField(_('Priority choice enabled'), 
                                                  default=settings.COSINNUS_CONFERENCE_PRIORITY_CHOICE_DEFAULT)
    

    @property
    def applications_are_active(self):
        if self.application_start and self.application_end:
            now = timezone.now()
            return now >= self.application_start and now <= self.application_end
        return True

    @property
    def application_time_string(self):
        if self.applications_are_active:
            return _('Participation applications are open.')
        else:
            now = timezone.now()
            if now < self.application_start:
                return _('Participation application has not started yet.')
            elif now > self.application_end:
                return _('Participation application is over.')

    @property
    def has_conditions(self):
        return bool(self.application_conditions_upload or self.application_conditions)
    
    @property
    def from_date(self):
        return self.application_start
    
    @property
    def to_date(self):
        return self.application_end


APPLICATION_INVALID = 1
APPLICATION_SUBMITTED = 2
APPLICATION_WAITLIST = 3
APPLICATION_ACCEPTED = 4
APPLICATION_DECLINED = 5

APPLICATION_STATES = [
    (APPLICATION_INVALID, pgettext_lazy('a conference application status', 'Invalid')),
    (APPLICATION_SUBMITTED, pgettext_lazy('a conference application status', 'Submitted')),
    (APPLICATION_WAITLIST, pgettext_lazy('a conference application status', 'Waitlist')),
    (APPLICATION_ACCEPTED, pgettext_lazy('a conference application status', 'Accepted')),
    (APPLICATION_DECLINED, pgettext_lazy('a conference application status', 'Declined')),
]

APPLICATION_STATES_MESSAGES = [
    (APPLICATION_INVALID, _('Your application is invalid.')),
    (APPLICATION_SUBMITTED, _('Your application has been submitted. You will be notified when it is processed.')),
    (APPLICATION_WAITLIST, _('Your application is currently on the waiting list.')),
    (APPLICATION_ACCEPTED, _('Your application has been accepted!')),
    (APPLICATION_DECLINED, _('We are sorry, but your application has been declined.')),
]

APPLICATION_STATES_ICONS = [
    (APPLICATION_INVALID, 'fa-times'),
    (APPLICATION_SUBMITTED, 'fa-spinner'),
    (APPLICATION_WAITLIST, 'fa-clock'),
    (APPLICATION_ACCEPTED, 'fa-check'),
    (APPLICATION_DECLINED, 'fa-times'),
]

APPLICATION_STATES_VISIBLE = [
    (APPLICATION_DECLINED, _('Declined')),
    (APPLICATION_WAITLIST, _('Waitlist')),
    (APPLICATION_ACCEPTED, _('Accepted')),
]

class CosinnusConferenceApplicationQuerySet(models.QuerySet):
    
    def active(self):
        return self.filter(conference__is_active=True)
    
    def order_by_conference_startdate(self):
        return self.active().order_by('conference__from_date')
    
    def pending_current(self):
        """ Returns all pending applications with conference to_date in the future """
        now = timezone.now()
        pending = [APPLICATION_SUBMITTED, APPLICATION_WAITLIST]
        return self.active()\
                   .filter(conference__to_date__gte=now)\
                   .filter(status__in=pending)\
                   .order_by('conference__from_date')

    def accepted_current(self):
        now = timezone.now()
        rejected = [APPLICATION_INVALID, APPLICATION_DECLINED]
        return self.active()\
                   .filter(conference__to_date__gte=now)\
                   .exclude(status__in=rejected)\
                   .order_by('conference__from_date')

    def accepted_in_past(self):
        now = timezone.now()
        return self.active().filter(conference__to_date__lte=now, status=APPLICATION_ACCEPTED)
    
    def declined_in_past(self):
        now = timezone.now()
        return self.active().filter(conference__to_date__lte=now, status=APPLICATION_DECLINED)
    
    def applied(self):
        return self.active().filter(status=APPLICATION_SUBMITTED)

    def pending(self):
        pending = [APPLICATION_SUBMITTED, APPLICATION_WAITLIST]
        return self.active().filter(status__in=pending)


class CosinnusConferenceApplication(models.Model):
    """ A model for an application to attend a conference, submitted by a user. """

    conference = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL,
                                           verbose_name=_('Confernence Application'),
                                           related_name='conference_applications',
                                           on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        related_name='user_applications', on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(choices=APPLICATION_STATES,
                                              default=APPLICATION_SUBMITTED)
    options = PostgresJSONField(default=list, blank=True, null=True)
    priorities = PostgresJSONField(_('Priorities'), default=dict, blank=True, null=True)
    information = models.TextField(_('Motivation for applying'), blank=True)
    contact_email = models.EmailField(_('Contact E-Mail Address'), blank=True, null=True)
    contact_phone = PhoneNumberField(('Contact Phone Number'), blank=True, null=True)
    
    reason_for_rejection = models.TextField(blank=True)
    
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    last_modified = models.DateTimeField(verbose_name=_('Last modified'), editable=False, auto_now=True)

    objects = CosinnusConferenceApplicationQuerySet.as_manager()
    
    class Meta(object):
        ordering = ('created',)
        verbose_name = _('Cosinnus conference application')
        verbose_name_plural = _('Cosinnus conference applications')
    
    @property
    def first_priorities(self):
        from cosinnus_event.models import Event # noqa
        return [Event.objects.get(id=int(key))
                for key,value in self.priorities.items() if value == 1]

    @property
    def second_priorities(self):
        from cosinnus_event.models import Event # noqa
        return [Event.objects.get(id=int(key))
                for key,value in self.priorities.items() if value == 2]

    @property
    def first_priorities_string(self):
        return ', '.join(event.title for event in self.first_priorities)

    @property
    def second_priorities_string(self):
        return ', '.join(event.title for event in self.second_priorities)

    @property
    def application_status_string(self):
        for message in APPLICATION_STATES_MESSAGES:
            if message[0] == self.status:
                return message[1]

    def get_icon(self):
        """ Returns the icon depending on the status of the application """
        for icon in APPLICATION_STATES_ICONS:
            if icon[0] == self.status:
                return icon[1]
    
    @property
    def email_notification_body(self):
        """ The description text for a notification email for this application
            for the application's user. The body text of the notification item
            that the user receives when their application is accepted/declined/waitlisted. """
        reason_markdown = ''
        if self.status in [APPLICATION_WAITLIST, APPLICATION_DECLINED] and self.reason_for_rejection:
            note_string = _('Note from the organizers')
            reason_markdown = f'**{note_string}:**\n\n{self.reason_for_rejection}'
        return reason_markdown or self.conference.description_long or self.conference.description or ''
    
    @property
    def group(self):
        """ Needed for notifications to know the group of this item """
        return self.conference
    
    def grant_extra_read_permissions(self, user):
        return self.user == user or check_user_superuser(user)
    
    def special_alert_check(self, user):
        """ Users want alerts for conference they applied to """
        return self.user == user
    
    def user_email(self):
        """ Needed for django-admin """
        return self.user.email



class CosinnusConferencePremiumBlock(models.Model):
    """ Signifies the time frames during which CosinnusConferences are set into premium mode by a 
        cronjob that switches their `is_premium_currently` flag. While this flag is True,
        the BBB URLs for all rooms/events within this conference will use the server config set 
        in the `CosinnusConferenceSettings.bbb_server_choice_premium` for each settings object
        inherited or set for each conference event.  """
    
    conference = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL,
                                           verbose_name=_('Conference'),
                                           related_name='conference_premium_blocks',
                                           on_delete=models.CASCADE)
    
    from_date = models.DateField(_('Start Datetime'), default=None, blank=True, null=True,
                                     help_text=_('During this time, the conference will be using the premium BBB server.'))
    to_date = models.DateField(_('End Datetime'), default=None, blank=True, null=True,
                                     help_text=_('During this time, the conference will be using the premium BBB server.'))
    participants = models.PositiveIntegerField(verbose_name=_('Conference participants'), default=0,
                                                   help_text=_('The number of BBB participants that have been declared will take part in the conference during this time. This is only a guideline for portal admins.'))
    
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    last_modified = models.DateTimeField(verbose_name=_('Last modified'), editable=False, auto_now=True)
    
    class Meta(object):
        ordering = ('from_date',)
        verbose_name = _('Cosinnus Conference Premium Block')
        verbose_name_plural = _('Cosinnus Conference Premium Blocks')
        
    def save(self, *args, **kwargs):
        """ Do the check for whether or not the conference for this block should be premium after saving """
        super(CosinnusConferencePremiumBlock, self).save(*args, **kwargs)
        from cosinnus_conference.utils import update_conference_premium_status
        update_conference_premium_status(conferences=[self.conference])
    


class CosinnusConferencePremiumCapacityInfo(models.Model):
    """ A guiding-only info for portal admins, during which times the premium BBB server can take 
        which capacity of users. Serves as a guideline for portal admins when they accept conferences
        as premium conference, to decide whether additional capacity on the BBB cluster should be booked. """
    
    portal = models.ForeignKey('cosinnus.CosinnusPortal',
                               verbose_name=_('Portal'),
                               related_name='portal_premium_capacity_blocks',
                               on_delete=models.CASCADE)
    
    from_date = models.DateField(_('Start Datetime'), default=None, blank=True, null=True,
                                     help_text=_('The time frame while the selected capacity is available.'))
    to_date = models.DateField(_('End Datetime'), default=None, blank=True, null=True,
                                     help_text=_('The time frame while the selected capacity is available.'))
    max_participants = models.PositiveIntegerField(verbose_name=_('Maximum BBB participants'), default=0,
                                                   help_text=_('The maximum number of BBB participants that should be allowed for all premium conferences. This is only a guideline for portal admins.'))
    
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    last_modified = models.DateTimeField(verbose_name=_('Last modified'), editable=False, auto_now=True)
    
    class Meta(object):
        ordering = ('from_date',)
        verbose_name = _('Conference Total Premium Capacity Info')
        verbose_name_plural = _('Conference Total Premium Capacity Infos')
    
