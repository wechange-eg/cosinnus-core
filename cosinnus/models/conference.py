# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import locale

from django.contrib.postgres.fields import JSONField as PostgresJSONField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
import six

from cosinnus.conf import settings
from cosinnus.utils.files import get_conference_conditions_filename
from cosinnus.models.group import CosinnusPortal
from cosinnus.utils.functions import clean_single_line_text, \
    unique_aware_slugify
from cosinnus.utils.urls import group_aware_reverse
from django.utils.crypto import get_random_string
import logging
from cosinnus.views.mixins.group import ModelInheritsGroupReadWritePermissionsMixin
from cosinnus.utils.permissions import check_user_superuser

logger = logging.getLogger('cosinnus')


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
class CosinnusConferenceRoom(ModelInheritsGroupReadWritePermissionsMixin, models.Model):
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


class ParticipationManagement(models.Model):

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
    
    def order_by_conference_startdate(self):
        return self.order_by('conference__from_date')
    
    def pending_current(self):
        """ Returns all pending applications with conference to_date in the future """
        now = timezone.now()
        pending = [APPLICATION_SUBMITTED, APPLICATION_WAITLIST]
        return self.filter(conference__to_date__gte=now)\
                   .filter(status__in=pending)\
                   .order_by('conference__from_date')

    def accepted_current(self):
        now = timezone.now()
        rejected = [APPLICATION_INVALID, APPLICATION_DECLINED]
        return self.filter(conference__to_date__gte=now)\
                   .exclude(status__in=rejected)\
                   .order_by('conference__from_date')

    def accepted_in_past(self):
        now = timezone.now()
        return self.filter(conference__to_date__lte=now, status=APPLICATION_ACCEPTED)
    
    def applied(self):
        return self.filter(status=APPLICATION_SUBMITTED)

    def pending(self):
        pending = [APPLICATION_SUBMITTED, APPLICATION_WAITLIST]
        return self.filter(status__in=pending)


class CosinnusConferenceApplication(models.Model):

    conference = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL,
                                           verbose_name=_('Confernence Application'),
                                           related_name='conference_applications',
                                           on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        related_name='user_applications', on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(choices=APPLICATION_STATES,
                                              default=APPLICATION_SUBMITTED)
    options = PostgresJSONField(default=list, blank=True, null=True)
    priorities = PostgresJSONField(default=dict, blank=True, null=True)
    information = models.TextField(blank=True)
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

