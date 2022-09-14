# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import datetime
import logging
from osm_field.fields import OSMField, LatitudeField, LongitudeField
import time
from uuid import uuid1

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.timezone import localtime, now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy, pgettext_lazy as p_
import six

from cosinnus.models import BaseTaggableObjectModel
from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.mixins.translations import TranslateableFieldsModelMixin
from cosinnus.models.tagged import LikeableObjectMixin
from cosinnus.utils.dates import localize, HumanizedEventTimeMixin
from cosinnus.utils.files import _get_avatar_filename, get_presentation_filename
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user, \
    check_object_read_access
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.validators import validate_file_infection
from cosinnus.views.mixins.reflected_objects import MixReflectedObjectsMixin
from cosinnus_event import cosinnus_notifications
from cosinnus_event.conf import settings
from cosinnus_event.fields import RTMPURLField
from cosinnus_event.managers import EventQuerySet
from cosinnus_event.mixins import BBBRoomMixin
from cosinnus_event.utils.bbb_streaming import trigger_streamer_status_changes


logger = logging.getLogger('cosinnus')


def get_event_image_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'images', 'events')

@six.python_2_unicode_compatible
class Event(HumanizedEventTimeMixin, TranslateableFieldsModelMixin, LikeableObjectMixin, 
            BBBRoomMixin, BaseTaggableObjectModel):

    SORT_FIELDS_ALIASES = [
        ('title', 'title'),
            ('from_date', 'from_date'),
        ('to_date', 'to_date'),
        ('city', 'city'),
        ('state', 'state'),
    ]

    STATE_SCHEDULED = 1
    STATE_VOTING_OPEN = 2
    STATE_CANCELED = 3
    STATE_ARCHIVED_DOODLE = 4

    STATE_CHOICES = (
        (STATE_SCHEDULED, _('Scheduled')),
        (STATE_VOTING_OPEN, _('Voting open')),
        (STATE_CANCELED, _('Canceled')),
        (STATE_ARCHIVED_DOODLE, _('Archived Event Poll')),
    )

    from_date = models.DateTimeField(
        _('Start'), default=None, blank=True, null=True, editable=True)

    to_date = models.DateTimeField(
        _('End'), default=None, blank=True, null=True, editable=True)

    state = models.PositiveIntegerField(
        _('State'),
        choices=STATE_CHOICES,
        default=STATE_VOTING_OPEN,
    )
    __state = None # pre-save purpose
    
    # used as special flag for a hidden conference event
    # that mimics the conference and can be used in normal Event querysets as proxy for the conference
    # the logic for this is in `cosinnus_event.hooks`
    is_hidden_group_proxy = models.BooleanField(_('Is hidden proxy'),
        help_text='If set, this event is hidden in its own group, acting as a proxy for the group with from_date and to_date synced, to be able to be shown in other groups.',
        default=False)

    note = models.TextField(_('Note'), blank=True, null=True)

    suggestion = models.ForeignKey(
        'Suggestion',
        verbose_name=_('Event date'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='selected_name',
    )

    NO_VIDEO_CONFERENCE = 0
    BBB_MEETING = 1
    FAIRMEETING = 2

    VIDEO_CONFERENCE_TYPE_CHOICES = (
        (BBB_MEETING, _('BBB-Meeting')),
        (FAIRMEETING, _('Fairmeeting')),
        (NO_VIDEO_CONFERENCE, _('No video conference')),
    )

    video_conference_type = models.PositiveIntegerField(
        _('Type of video conference available for the event'), blank=False, null=False, choices=VIDEO_CONFERENCE_TYPE_CHOICES, default=NO_VIDEO_CONFERENCE,)
    
    # DEPRECATED: use `media_tag.location` instead!
    location = OSMField(_('Location'), blank=True, null=True)
    # DEPRECATED: use `media_tag.location` instead!
    location_lat = LatitudeField(_('Latitude'), blank=True, null=True)
    # DEPRECATED: use `media_tag.location` instead!
    location_lon = LongitudeField(_('Longitude'), blank=True, null=True)
    
    # DEPRECATED: use `media_tag.location` instead!
    street = models.CharField(_('Street'), blank=True, max_length=50, null=True)
    
    # DEPRECATED: use `media_tag.location` instead!
    zipcode = models.PositiveIntegerField(_('ZIP code'), blank=True, null=True)

    # DEPRECATED: use `media_tag.location` instead!
    city = models.CharField(_('City'), blank=True, max_length=50, null=True)
    
    # DEPRECATED: use `media_tag.visibility` instead!
    public = models.BooleanField(_('Is public (on website)'), default=False)
    
    image = models.ImageField(
        _('Image'),
        upload_to=get_event_image_filename,
        blank=True,
        null=True)

    url = models.URLField(_('URL'), blank=True, null=True)
    
    original_doodle = models.OneToOneField("self", verbose_name=_('Original Event Poll'),
        related_name='scheduled_event', null=True, blank=True, on_delete=models.SET_NULL)
    
    objects = EventQuerySet.as_manager()
    
    timeline_template = 'cosinnus_event/v2/dashboard/timeline_item.html'

    class Meta(BaseTaggableObjectModel.Meta):
        ordering = ['from_date', 'to_date', 'title']
        verbose_name = _('Event')
        verbose_name_plural = _('Events')
        
    def __init__(self, *args, **kwargs):
        super(Event, self).__init__(*args, **kwargs)
        self.__state = self.state

    def __str__(self):
        if self.is_hidden_group_proxy:
            readable = _('%(event)s (hidden proxy)') % {'event': self.title}
        elif self.state == Event.STATE_SCHEDULED:
            if self.single_day:
                readable = _('%(event)s (%(date)s - %(end)s)') % {
                    'event': self.title,
                    'date': localize(self.from_date, 'd. F Y h:i'),
                    'end': localize(self.to_date, 'h:i'),
                }
            else:
                readable = _('%(event)s (%(from)s - %(to)s)') % {
                    'event': self.title,
                    'from': localize(self.from_date, 'd. F Y h:i'),
                    'to': localize(self.to_date, 'd. F Y h:i'),
                }
        elif self.state == Event.STATE_CANCELED:
            readable = _('%(event)s (canceled)') % {'event': self.title}
        elif self.state == Event.STATE_VOTING_OPEN:
            readable = _('%(event)s (pending)') % {'event': self.title}
        elif self.state == Event.STATE_ARCHIVED_DOODLE:
            readable = _('%(event)s (archived)') % {'event': self.title}
        else:
            readable = _('%(event)s (state unknown)') % {'event': self.title}
            
        return readable
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        if self.state == 2:
            return 'fa-calendar-check-o'
        else:
            return 'fa-calendar'
    
    def save(self, created_from_doodle=False, *args, **kwargs):
        created = bool(self.pk) == False
        super(Event, self).save(*args, **kwargs)

        if created and not self.is_hidden_group_proxy:
            # event/doodle was created or
            # event went from being a doodle to being a real event, so fire event created
            session_id = uuid1().int
            audience = get_user_model().objects.filter(id__in=self.group.members)
            if self.creator:
                audience = audience.exclude(id=self.creator.pk)
            group_followers_except_creator_ids = [pk for pk in self.group.get_followed_user_ids() if not pk in [self.creator_id]]
            group_followers_except_creator = get_user_model().objects.filter(id__in=group_followers_except_creator_ids)
            if self.state == Event.STATE_SCHEDULED:
                # followers for the group
                cosinnus_notifications.followed_group_event_created.send(sender=self, user=self.creator, obj=self, audience=group_followers_except_creator, session_id=session_id)
                # regular members
                cosinnus_notifications.event_created.send(sender=self, user=self.creator, obj=self, audience=audience, session_id=session_id, end_session=True)
            else:
                # followers for the group
                cosinnus_notifications.followed_group_doodle_created.send(sender=self, user=self.creator, obj=self, audience=group_followers_except_creator, session_id=session_id)
                # regular members
                cosinnus_notifications.doodle_created.send(sender=self, user=self.creator, obj=self, audience=audience, session_id=session_id, end_session=True)
            
        # create a "going" attendance for the event's creator
        if settings.COSINNUS_EVENT_MARK_CREATOR_AS_GOING and created and self.state == Event.STATE_SCHEDULED:
            EventAttendance.objects.get_or_create(event=self, user=self.creator, defaults={'state':EventAttendance.ATTENDANCE_GOING})
        
        self.__state = self.state

    def get_absolute_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        if self.state == Event.STATE_VOTING_OPEN:
            return group_aware_reverse('cosinnus:event:doodle-vote', kwargs=kwargs)
        elif self.state == Event.STATE_ARCHIVED_DOODLE:
            return group_aware_reverse('cosinnus:event:doodle-archived', kwargs=kwargs)
        elif self.is_hidden_group_proxy:
            # hidden proxy events redirect to the group
            return self.group.get_absolute_url()
        return group_aware_reverse('cosinnus:event:event-detail', kwargs=kwargs)
    
    def get_edit_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        if self.state == Event.STATE_VOTING_OPEN or self.state == Event.STATE_ARCHIVED_DOODLE:
            return group_aware_reverse('cosinnus:event:doodle-edit', kwargs=kwargs)
        elif self.is_hidden_group_proxy:
            # hidden proxy events redirect to the group
            return self.group.get_edit_url()
        return group_aware_reverse('cosinnus:event:event-edit', kwargs=kwargs)
    
    def get_delete_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        if self.state == Event.STATE_VOTING_OPEN or self.state == Event.STATE_ARCHIVED_DOODLE:
            return group_aware_reverse('cosinnus:event:doodle-delete', kwargs=kwargs)
        elif self.is_hidden_group_proxy:
            # hidden proxy events redirect to the group
            return self.group.get_delete_url()
        return group_aware_reverse('cosinnus:event:event-delete', kwargs=kwargs)
    
    def get_feed_url(self):
        """ Returns the iCal feed url. A user token as to be appended using either
            `cosinnus.utils.permission` or `cosinnus_tags.cosinnus_user_token` """
        kwargs = {'team_id': self.group.id, 'slug': self.slug}
        return group_aware_reverse('cosinnus:team-feed-entry', kwargs=kwargs)
    
    def is_user_attending(self, user):
        """ For notifications, statecheck if a user is attending this event """
        return self.attendances.filter(user=user, state__in=[EventAttendance.ATTENDANCE_GOING, EventAttendance.ATTENDANCE_MAYBE_GOING]).count() >= 1
    
    def special_alert_check(self, user):
        """ Can override checking whether this user wants this alert """
        return self.is_user_attending(user)
    
    @property
    def sort_key(self):
        """ Overriding this sort key so re-ordering won't happen for widgets using events 
            (because all event querysets are already well-sorted.) """
        return 0
    
    @property
    def stream_sort_key(self):
        """ Sort key for activity streams returns the created date instead of the event date """
        return self.created
            

    def set_suggestion(self, sugg=None, update_fields=['from_date', 'to_date', 'state', 'suggestion']):
        if sugg is None:
            # No suggestion selected or remove selection
            self.from_date = None
            self.to_date = None
            self.state = Event.STATE_VOTING_OPEN
            self.suggestion = None
        elif sugg.event.pk == self.pk:
            # Make sure to not assign a suggestion belonging to another event.
            self.from_date = sugg.from_date
            self.to_date = sugg.to_date
            self.state = Event.STATE_SCHEDULED
            self.suggestion = sugg
        else:
            return
        self.save(update_fields=update_fields)

    @classmethod
    def get_current(self, group, user, include_sub_projects=False):
        """ Returns a queryset of the current upcoming events """
        groups = [group]
        if include_sub_projects:
            groups = groups + list(group.get_children())
        
        qs = Event.objects.filter(group__in=groups).filter(state__in=[
                    Event.STATE_SCHEDULED, 
                    Event.STATE_VOTING_OPEN,
                ])
        
        if not include_sub_projects:
            # mix in reflected objects, not needed if we are sub-grouping anyways
            for onegroup in groups:
                if "%s.%s" % (self._meta.app_label, self._meta.model_name) in settings.COSINNUS_REFLECTABLE_OBJECTS:
                    mixin = MixReflectedObjectsMixin()
                    qs = mixin.mix_queryset(qs, self._meta.model, onegroup)
        if user:
            qs = filter_tagged_object_queryset_for_user(qs, user)
        return upcoming_event_filter(qs).distinct()
    
    @classmethod
    def get_current_for_portal(self):
        """ Returns a queryset of the current upcoming events in this portal """
        qs = Event.objects.filter(group__portal=CosinnusPortal.get_current()).filter(state__in=[Event.STATE_SCHEDULED])
        return upcoming_event_filter(qs)
    
    def get_voters_pks(self):
        """ Gets the pks of all Users that have voted for this event.
            Returns an empty list if nobody has voted or the event isn't a doodle. """
        return self.suggestions.all().values_list('votes__voter__id', flat=True).distinct()
    
    def get_suggestions_hash(self):
        """ Returns a hashable string containing all suggestions with their time.
            Useful to compare equality of suggestions for two doodles. """
        return ','.join([str(time.mktime(dt.timetuple())) for dt in self.suggestions.all().values_list('from_date', flat=True)])

    def get_comment_post_url(self):
        return group_aware_reverse('cosinnus:event:comment', kwargs={'group': self.group, 'event_slug': self.slug})
    
    def get_attendants_count(self):
        all_attendants = EventAttendance.objects.filter(event=self)
        attendants_going = all_attendants.filter(state=EventAttendance.ATTENDANCE_GOING)
        return attendants_going.count()
    
    def can_have_bbb_room(self):
        """ For BBBRoomMixin """
        return self.video_conference_type == self.BBB_MEETING
    
    def get_meeting_id_for_bbb_room(self):
        """ For BBBRoomMixin, this one uses the group id as well as the event """
        return f'{settings.COSINNUS_PORTAL_NAME}-{self.group.id}-{self.id}'

    def get_moderators_for_bbb_room(self):
        """ For BBBRoomMixin, overridable function to return a list of users that should be a moderator
            of this BBB room (with higher priviledges than a member) """
        moderators = super().get_moderators_for_bbb_room()
        moderators.append(self.creator)
        return moderators
    
    def get_admin_change_url(self):
        """ Returns the django admin edit page for this object. """
        return reverse('admin:cosinnus_event_event_change', kwargs={'object_id': self.id})
    

@six.python_2_unicode_compatible
class Suggestion(models.Model):
    from_date = models.DateTimeField(
        _('Start'), default=None, blank=False, null=False)

    to_date = models.DateTimeField(
        _('End'), default=None, blank=False, null=False)

    event = models.ForeignKey(
        Event,
        verbose_name=_('Event'),
        on_delete=models.CASCADE,
        related_name='suggestions',
    )

    count = models.PositiveIntegerField(
        pgettext_lazy('the subject', 'Votes'), default=0, editable=False)

    class Meta(object):
        ordering = ['event', '-count']
        unique_together = ('event', 'from_date', 'to_date')
        verbose_name = _('Suggestion')
        verbose_name_plural = _('Suggestions')

    def __str__(self):
        if self.single_day:
            if self.from_date == self.to_date:
                return '%(date)s' % {
                    'date': localize(self.from_date, 'd. F Y H:i'),
                }
            return '%(date)s - %(end)s' % {
                'date': localize(self.from_date, 'd. F Y H:i'),
                'end': localize(self.to_date, 'H:i'),
            }
        return '%(from)s - %(to)s' % {
            'from': localize(self.from_date, 'd. F Y H:i'),
            'to': localize(self.to_date, 'd. F Y H:i'),
        }

    def get_absolute_url(self):
        return self.event.get_absolute_url()

    def update_vote_count(self, count=None):
        self.count = self.votes.count()
        self.save(update_fields=['count'])

    @property
    def single_day(self):
        return localtime(self.from_date).date() == localtime(self.to_date).date()
    
    @cached_property
    def sorted_votes(self):
        return self.votes.order_by('voter__first_name', 'voter__last_name')

@six.python_2_unicode_compatible
class Vote(models.Model):
    
    VOTE_YES = 2
    VOTE_MAYBE = 1
    VOTE_NO = 0
    
    VOTE_CHOICES = (
        (VOTE_YES, _('Yes')),
        (VOTE_MAYBE, _('Maybe')),
        (VOTE_NO, _('No')),     
    )
    
    suggestion = models.ForeignKey(
        Suggestion,
        verbose_name=_('Suggestion'),
        on_delete=models.CASCADE,
        related_name='votes',
    )

    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Voter'),
        on_delete=models.CASCADE,
        related_name='votes',
    )
    
    choice = models.PositiveSmallIntegerField(_('Vote'), blank=False, null=False,
        default=VOTE_NO, choices=VOTE_CHOICES)
    

    class Meta(object):
        unique_together = ('suggestion', 'voter')
        verbose_name = pgettext_lazy('the subject', 'Vote')
        verbose_name_plural = pgettext_lazy('the subject', 'Votes')

    def __str__(self):
        return 'Vote for %(event)s: %(from)s - %(to)s' % {
            'event': self.suggestion.event.title,
            'from': localize(self.suggestion.from_date, 'd. F Y h:i'),
            'to': localize(self.suggestion.to_date, 'd. F Y h:i'),
        }

    def get_absolute_url(self):
        return self.suggestion.event.get_absolute_url()

@six.python_2_unicode_compatible
class EventAttendance(models.Model):
    """ Model for attendance choices of a User for an Event.
        The choices do not include a "no choice selected" state on purpose,
        as a user not having made a choice is modeled by a missing instance
        of ``EventAttendance`` for that user and event.
     """
    
    ATTENDANCE_NOT_GOING = 0
    ATTENDANCE_MAYBE_GOING = 1
    ATTENDANCE_GOING = 2
    
    ATTENDANCE_STATES = (
        (ATTENDANCE_NOT_GOING, p_('cosinnus_event_attendance', 'not going')),
        (ATTENDANCE_MAYBE_GOING, p_('cosinnus membership status', 'maybe going')),
        (ATTENDANCE_GOING, p_('cosinnus membership status', 'going')),
    )
    
    event = models.ForeignKey(Event, related_name='attendances', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        related_name='cosinnus_event_attendances', on_delete=models.CASCADE)
    state = models.PositiveSmallIntegerField(choices=ATTENDANCE_STATES,
        db_index=True, default=ATTENDANCE_NOT_GOING)
    date = models.DateTimeField(auto_now_add=True, editable=False)
    
    class Meta(object):
        unique_together = ('event', 'user', )
        
    def __str__(self):
        return "Event Attendance <user: %(user)s, event: %(event)s, state: %(state)d>" % {
            'user': self.user.email,
            'event': self.event.slug,
            'state': self.state,
        }
    

@six.python_2_unicode_compatible
class Comment(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Creator'), on_delete=models.PROTECT, related_name='event_comments')
    created_on = models.DateTimeField(_('Created'), default=now, editable=False)
    last_modified = models.DateTimeField(_('Last modified'), auto_now=True, editable=False)
    event = models.ForeignKey(Event, related_name='comments', on_delete=models.CASCADE)
    text = models.TextField(_('Text'))

    class Meta(object):
        ordering = ['created_on']
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __str__(self):
        return 'Comment on “%(event)s” by %(creator)s' % {
            'event': self.event.title,
            'creator': self.creator.get_full_name(),
        }
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        return 'fa-comment'
    
    @property
    def parent(self):
        """ Returns the parent object of this comment """
        return self.event
    
    def get_notification_hash_id(self):
        """ Overrides the item hashing for notification alert hashing, so that
            he parent item is considered as "the same" item, instead of this comment """
        return self.parent.id

    def get_absolute_url(self):
        if self.pk:
            return '%s#comment-%d' % (self.event.get_absolute_url(), self.pk)
        return self.event.get_absolute_url()
    
    def get_edit_url(self):
        return group_aware_reverse('cosinnus:event:comment-update', kwargs={'group': self.event.group, 'pk': self.pk})

    def get_delete_url(self):
        return group_aware_reverse('cosinnus:event:comment-delete', kwargs={'group': self.event.group, 'pk': self.pk})
    
    def is_user_following(self, user):
        """ Delegates to parent object """
        return self.event.is_user_following(user)
    
    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Comment, self).save(*args, **kwargs)
        
        already_messaged_user_pks = []
        if created:
            session_id = uuid1().int
            # comment was created, message event creator
            if not self.event.creator == self.creator:
                cosinnus_notifications.event_comment_posted.send(sender=self, user=self.creator, obj=self, audience=[self.event.creator], session_id=session_id)
                already_messaged_user_pks += [self.event.creator_id]
                
            # message all followers of the event
            followers_except_creator = [pk for pk in self.event.get_followed_user_ids() if not pk in [self.creator_id, self.event.creator_id]]
            cosinnus_notifications.following_event_comment_posted.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=followers_except_creator), session_id=session_id)
            
            # message votees (except comment creator and event creator) if voting is still open
            if self.event.state == Event.STATE_VOTING_OPEN:
                votees_except_creator = [pk for pk in self.event.get_voters_pks() if not pk in [self.creator_id, self.event.creator_id]]
                cosinnus_notifications.voted_event_comment_posted.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=votees_except_creator), session_id=session_id)
                already_messaged_user_pks += votees_except_creator
                    
                
            # message all attending persons (GOING and MAYBE_GOING)
            if self.event.state == Event.STATE_SCHEDULED:
                attendees_except_creator = [attendance.user.pk for attendance in self.event.attendances.all() \
                            if (attendance.state in [EventAttendance.ATTENDANCE_GOING, EventAttendance.ATTENDANCE_MAYBE_GOING])\
                                and not attendance.user.pk in [self.creator_id, self.event.creator_id]]
                cosinnus_notifications.attending_event_comment_posted.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=attendees_except_creator), session_id=session_id)
                already_messaged_user_pks += attendees_except_creator
                
            # message all taggees (except comment creator)
            if self.event.media_tag and self.event.media_tag.persons:
                tagged_users_without_self = self.event.media_tag.persons.exclude(id__in=already_messaged_user_pks+[self.creator.id])
                cosinnus_notifications.tagged_event_comment_posted.send(sender=self, user=self.creator, obj=self, audience=list(tagged_users_without_self), session_id=session_id)
            
            # end notification session
            cosinnus_notifications.tagged_event_comment_posted.send(sender=self, user=self.creator, obj=self, audience=[], session_id=session_id, end_session=True)
            
            
    @property
    def group(self):
        """ Needed by the notifications system """
        return self.event.group
    
    def grant_extra_read_permissions(self, user):
        """ Comments inherit their visibility from their commented on parent """
        return check_object_read_access(self.event, user)



@six.python_2_unicode_compatible
class ConferenceEvent(Event):
    
    # translatable fields are only enabled for conference events for now
    if settings.COSINNUS_TRANSLATED_FIELDS_ENABLED:
        translateable_fields = ['title', 'note']
    
    TYPE_LOBBY_CHECKIN = 0
    TYPE_STAGE_EVENT = 1
    TYPE_WORKSHOP = 2
    TYPE_DISCUSSION = 3
    TYPE_COFFEE_TABLE = 4
    
    TYPE_CHOICES = (
        (TYPE_LOBBY_CHECKIN, _('Lobby Check-in Event')),
        (TYPE_STAGE_EVENT, _('Stage Stream')),
        (TYPE_WORKSHOP, _('Workshop')),
        (TYPE_DISCUSSION, _('Discussion')),
        (TYPE_COFFEE_TABLE, _('Coffee Table')),
    )
    
    CONFERENCE_EVENT_TYPE_BY_ROOM_TYPE = {
        CosinnusConferenceRoom.TYPE_LOBBY: TYPE_LOBBY_CHECKIN,
        CosinnusConferenceRoom.TYPE_STAGE: TYPE_STAGE_EVENT,
        CosinnusConferenceRoom.TYPE_WORKSHOPS: TYPE_WORKSHOP,
        CosinnusConferenceRoom.TYPE_DISCUSSIONS: TYPE_DISCUSSION,
        CosinnusConferenceRoom.TYPE_COFFEE_TABLES: TYPE_COFFEE_TABLE,
    }
    
    # rooms of these types will initialize a corresponding `BBBRoom` in the media_tag
    BBB_ROOM_TYPES = (
        TYPE_WORKSHOP,
        TYPE_COFFEE_TABLE,
        TYPE_DISCUSSION,
    )
    
    # maps ConferenceEvent types to bbb-room natures. see `BBBRoomMixin.get_bbb_room_nature()`
    BBB_ROOM_NATURE_MAP = {
        TYPE_COFFEE_TABLE: 'coffee',
    }

    TIMELESS_TYPES = (
        TYPE_COFFEE_TABLE,
    )
    
    BBB_MAX_PARTICIPANT_TYPES = BBB_ROOM_TYPES
    
    # the room this conference event is in. 
    # the conference event type will be set according to the room type of this room
    room = models.ForeignKey('cosinnus.CosinnusConferenceRoom', verbose_name=_('Room'),
        related_name='events', on_delete=models.CASCADE)
    
    # may not be changed after creation!
    type = models.PositiveSmallIntegerField(_('Conference Event Type'), blank=False,
        default=TYPE_WORKSHOP, choices=TYPE_CHOICES)

    # list of presenters/moderators that should be     
    presenters = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        verbose_name=_('Presenters'), related_name='+',
        help_text='A list of users that will be displayed as presenters and become BBB moderators in attached rooms')

    # Type: Workshop, Discussion
    is_break = models.BooleanField(_('Is a Break'),
        help_text='If an event is a break, no rooms will be created for it, and it will be displayed differently',
        default=False)

    # Checkbox for visible / hidden mode of the particular conference event on the conference microsite
    is_visible_on_microsite = models.BooleanField(_('Event is visible on the conference microsite'),
        help_text='Provides an option to choose if the particular conference event should be shown on microsite or not',
        default=True)

    # Checkbox for visible / hidden mode of the conference event's description on the conference microsite 
    is_description_visible_on_microsite = models.BooleanField(_('Event\'s description is visible on the conference microsite'),
        help_text='Provides an option to choose if the particular conference event\'s description should be shown on microsite or not',
        default=True)
    
    # Type: Coffee-Tables
    max_participants = models.PositiveSmallIntegerField(_('Maximum Event Participants'),
        blank=False, default=settings.COSINNUS_CONFERENCE_COFFEETABLES_MAX_PARTICIPANTS_DEFAULT,
        validators=[MinValueValidator(2), MaxValueValidator(512)])

    raw_html = models.TextField(_('Embed code (HTML)'),
        help_text='Raw HTML embed code to use instead of URL',
        blank=True, null=True,
        default='')

    presentation_file = models.FileField(_('Presentation file'),
        help_text='The presentation file (e.g. PDF) will be pre-uploaded to the BBB room.',
        null=True, blank=True, upload_to=get_presentation_filename,
        validators=[validate_file_infection])
    
    # flag to enable/disable rocket chat showing in this event
    show_chat = models.BooleanField(_('Show chat'),
        help_text='Show rocket chat in sidebar in event',
        default=False)
    
    # flag to enable/disable rocket chat showing in this event
    enable_streaming = models.BooleanField(_('Enable Streaming'),
        default=False)
    
    stream_url = RTMPURLField(_('Stream URL'), 
        help_text=_('The URL of your streaming provider to receive the incoming stream'),
        blank=True, null=True)
    
    stream_key = models.CharField(_('Stream Key'), 
        help_text=_('The key for this specific stream session you created at your streaming provider'),
        blank=True, max_length=250, null=True)

    class Meta(BaseTaggableObjectModel.Meta):
        ordering = ['from_date', 'to_date', 'title']
        verbose_name = _('Conference Event')
        verbose_name_plural = _('Conference Events')
        unique_together = None

    def __init__(self, *args, **kwargs):
        super(ConferenceEvent, self).__init__(*args, **kwargs)

    def __str__(self):
        readable = _('%(event)s %(type)s') % {'event': self.title, 'type': self.type}
        return readable

    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        if created:
            self.type = self.CONFERENCE_EVENT_TYPE_BY_ROOM_TYPE.get(self.room.type, None)
            if self.type is None:
                raise ImproperlyConfigured('Conference Event type not found for room type "%s"' % self.room.type)
        
        # important: super(Event), not ConferenceEvent, because we don't want to inherit the notifiers
        super(Event, self).save(*args, **kwargs)
        
        # trigger any streamer status changes if enabled, so streamers
        # are started/stopped instantly on changes
        trigger_streamer_status_changes(events=[self])

        # create a "going" attendance for the event's creator
        if settings.COSINNUS_EVENT_MARK_CREATOR_AS_GOING and created and self.state == ConferenceEvent.STATE_SCHEDULED:
            EventAttendance.objects.get_or_create(event=self, user=self.creator, defaults={'state':EventAttendance.ATTENDANCE_GOING})
    
    def can_have_bbb_room(self):
        """ Check if this event may have a BBB room """
        return self.type in self.BBB_ROOM_TYPES and not self.is_break 
    
    def get_bbb_room_nature(self):
        """ Set the nature for coffee tables.
        
            Method to set the nature for a bbb-room depending on its type of source object.
            A nature for a bbb room is a property that determines differences in its 
            create/join API-call parameters that can be configured via
            `settings.BBB_PARAM_PORTAL_DEFAULTS or dynamically in the 
            `CosinnusConferenceSettings.bbb_params` json-field of each configuration object.
            These may be set by an admin or dynamically using presets fields. 
            
            This allows bbb rooms to behave differently depending on what type of conference event
            they are displayed in, like the instant-join nature of CoffeeTables
            
            A nature will be retrieved during CosinnusConferenceSettings agglomeration time,
            from the source object through this method, and set for the settings object itself.
            When the bbb params are retrieved for a BBB-API call like create/join using 
            `CosinnusConferenceSettings.get_finalized_bbb_params` the nature-specific call params
            for the set nature are merged over the base non-nature params of that settings object.
            
            Example: for a 'coffee' nature, the 'join__coffee' api-call param key in the JSON
                is merged over the 'join' api-call param key.
                
            @return: a nature string or None
        """
        return self.BBB_ROOM_NATURE_MAP.get(self.type, None)
    
    def get_max_participants(self):
        """ For BBBRoomMixin, returns the number of participants allowed in the room
            @param return: a number between 0-999. """
        max_participants = None
        if self.type in self.BBB_MAX_PARTICIPANT_TYPES and self.max_participants:
            max_participants = self.max_participants
        # monkeypatch for BBB appearently allowing one less persons to enter a room
        if max_participants is not None and settings.BBB_ROOM_FIX_PARTICIPANT_COUNT_PLUS_ONE:
            max_participants += 1
        return max_participants
    
    def get_presentation_url(self):
        """ For BBBRoomMixin. the presentation URL used in create calls """ 
        return self.presentation_file.url if self.presentation_file else None
    
    def get_meeting_id_for_bbb_room(self):
        """ For BBBRoomMixin, this one uses the group id as well as the event """
        return f'{settings.COSINNUS_PORTAL_NAME}-{self.group.id}-{self.id}'
    
    def get_moderators_for_bbb_room(self):
        """ For BBBRoomMixin, overridable function to return a list of users that should be a moderator
            of this BBB room (with higher priviledges than a member) """
        moderators = super().get_moderators_for_bbb_room()
        moderators.append(self.creator)
        moderators.extend(list(self.presenters.all()))
        return moderators
    
    def get_absolute_url(self):
        if settings.COSINNUS_CONFERENCES_USE_COMPACT_MODE:
            return super(ConferenceEvent, self).get_absolute_url()
        return group_aware_reverse('cosinnus:conference:room-event', kwargs={'group': self.group, 'slug': self.room.slug, 'event_id': self.id}).replace('%23/', '#/')
    
    def get_edit_url(self):
        return group_aware_reverse('cosinnus:event:conference-event-edit', kwargs={'group': self.group, 'room_slug': self.room.slug, 'slug': self.slug})
    
    def get_delete_url(self):
        return group_aware_reverse('cosinnus:event:conference-event-delete', kwargs={'group': self.group, 'room_slug': self.room.slug, 'slug': self.slug})
    
    def get_admin_change_url(self):
        """ Returns the django admin edit page for this object. """
        return reverse('admin:cosinnus_event_conferenceevent_change', kwargs={'object_id': self.id})
    
    def get_type_verbose(self):
        return dict(self.TYPE_CHOICES).get(self.type, '(unknown type)')

    @property
    def streaming_allowed(self):
        group = self.room.group
        settings_allow_streaming = (settings.COSINNUS_CONFERENCES_STREAMING_ENABLED and
                                    settings.COSINNUS_PREMIUM_CONFERENCES_ENABLED)
        return group.has_premium_rights and settings_allow_streaming


@receiver(post_delete, sender=Vote)
def post_vote_delete(sender, **kwargs):
    try:
        kwargs['instance'].suggestion.update_vote_count()
    except Suggestion.DoesNotExist:
        pass


@receiver(post_save, sender=Vote)
def post_vote_save(sender, **kwargs):
    kwargs['instance'].suggestion.update_vote_count()


def get_past_event_filter_expression():
    """ Returns the filter expression that defines all events that were finished before <now>. """
    _now = now()
    event_horizon = datetime.datetime(_now.year, _now.month, _now.day)
    return Q(to_date__lt=event_horizon) | (Q(to_date__isnull=True) & Q(from_date__lt=event_horizon))
   
def upcoming_event_filter(queryset):
    """ Filters a queryset of events for events that begin in the future, 
    or have an end date in the future. Will always show all events that ended today as well. """
    return queryset.exclude(get_past_event_filter_expression())

def past_event_filter(queryset):
    """ Filters a queryset of events for events that began before today, 
    or have an end date before today. """
    return queryset.filter(get_past_event_filter_expression())


def annotate_attendants_count(qs):
    """ Utility function to annotate the number of GOING attendants for 
        an Event QS. """
    return qs.annotate(
            attendants_count=models.Count(
                models.Case(
                    models.When(attendances__state=EventAttendance.ATTENDANCE_GOING, then=1),
                        default=0, output_field=models.IntegerField()
                )
            )
        )
