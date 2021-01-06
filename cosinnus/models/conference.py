# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import locale

from django.contrib.postgres.fields import JSONField as PostgresJSONField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
import six

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.utils.functions import clean_single_line_text, \
    unique_aware_slugify
from cosinnus.utils.urls import group_aware_reverse
from django.utils.crypto import get_random_string
import logging
from cosinnus.views.mixins.group import ModelInheritsGroupReadWritePermissionsMixin

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
        if not settings.COSINNUS_ROCKET_ENABLED or not self.type in self.ROCKETCHAT_ROOM_TYPES:
            return ''
        if not self.rocket_chat_room_id or not self.rocket_chat_room_name:
            self.ensure_room_type_dependencies()
        if not self.rocket_chat_room_id or not self.rocket_chat_room_name:
            return ''
        room_id = self.rocket_chat_room_name
        return f'{settings.COSINNUS_CHAT_BASE_URL}/group/{room_id}/?layout=embedded'
    
    def ensure_room_type_dependencies(self):
        """ Depending on a room type, initialize different extras like rocketchat rooms """
        if settings.COSINNUS_ROCKET_ENABLED and self.type in self.ROCKETCHAT_ROOM_TYPES:
            self.sync_rocketchat_room()
    
    def sync_rocketchat_room(self, force=False):
        """ Can be safely called with force=False without re-creating rooms """
        if settings.COSINNUS_ROCKET_ENABLED and self.type in self.ROCKETCHAT_ROOM_TYPES:
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
    application_options = PostgresJSONField(default=list, blank=True, null=True)
    conference = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL,
                                           verbose_name=_('Participation Management'),
                                           related_name='participation_management',
                                           on_delete=models.CASCADE)