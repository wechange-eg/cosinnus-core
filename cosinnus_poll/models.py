# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object, str
from uuid import uuid1

import django
import six
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from cosinnus.models import BaseTaggableObjectModel
from cosinnus.models.mixins.images import ThumbnailableImageMixin
from cosinnus.models.tagged import LikeableObjectMixin
from cosinnus.utils.files import _get_avatar_filename
from cosinnus.utils.permissions import check_object_read_access, filter_tagged_object_queryset_for_user
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_poll import cosinnus_notifications
from cosinnus_poll.conf import settings
from cosinnus_poll.managers import PollManager


def get_poll_image_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'images', 'polls')


@six.python_2_unicode_compatible
class Poll(LikeableObjectMixin, BaseTaggableObjectModel):
    """Model for polls."""

    SORT_FIELDS_ALIASES = [
        ('title', 'title'),
    ]

    STATE_VOTING_OPEN = 1
    STATE_CLOSED = 2
    STATE_ARCHIVED = 3

    STATE_CHOICES = (
        (STATE_VOTING_OPEN, _('Voting open')),
        (STATE_CLOSED, _('Voting closed')),
        (STATE_ARCHIVED, _('Poll archived')),
    )

    state = models.PositiveIntegerField(
        _('State'),
        choices=STATE_CHOICES,
        default=STATE_VOTING_OPEN,
    )
    description = models.TextField(_('Description'), blank=True, null=True)

    multiple_votes = models.BooleanField(
        _('Multiple options votable'),
        default=True,
        help_text=_('Does this poll allow users to vote on multiple options or just decide for one?'),
    )
    can_vote_maybe = models.BooleanField(
        _('"Maybe" option enabled'),
        default=True,
        help_text=_('Is the maybe option enabled? Ignored and defaulting to False if ``multiple_votes==False``'),
    )
    anyone_can_vote = models.BooleanField(
        _('Anyone can vote'),
        default=False,
        help_text=_('If true, anyone who can see this poll can vote on it. If false, only group members can.'),
    )
    show_voters = models.BooleanField(
        _('Show voters'), default=False, help_text=_('If true, display a list of which user voted for each option.')
    )

    closed_date = models.DateTimeField(_('Start'), default=None, blank=True, null=True, editable=True)
    winning_option = models.ForeignKey(
        'Option',
        verbose_name=_('Winning Option'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='selected_name',
    )

    __state = None  # pre-save purpose

    objects = PollManager()

    timeline_template = 'cosinnus_poll/v2/dashboard/timeline_item.html'

    class Meta(BaseTaggableObjectModel.Meta):
        ordering = ['-created', '-closed_date']
        verbose_name = _('Poll')
        verbose_name_plural = _('Polls')

    def __init__(self, *args, **kwargs):
        super(Poll, self).__init__(*args, **kwargs)
        self.__state = self.state

    def __str__(self):
        if self.state == self.STATE_VOTING_OPEN:
            state_verbose = 'open'
        else:
            state_verbose = 'closed'
        readable = _('Poll: %(poll)s (%(state)s)') % {'poll': self.title, 'state': state_verbose}
        return readable

    def get_icon(self):
        """Returns the font-awesome icon specific to this object type"""
        return 'fa-bar-chart'

    def save(self, *args, **kwargs):
        created = bool(self.pk) is False
        super(Poll, self).save(*args, **kwargs)

        session_id = uuid1().int
        if created:
            group_followers_except_creator_ids = [
                pk for pk in self.group.get_followed_user_ids() if pk not in [self.creator_id]
            ]
            group_followers_except_creator = get_user_model().objects.filter(id__in=group_followers_except_creator_ids)
            cosinnus_notifications.followed_group_poll_created.send(
                sender=self, user=self.creator, obj=self, audience=group_followers_except_creator, session_id=session_id
            )
            cosinnus_notifications.poll_created.send(
                sender=self,
                user=self.creator,
                obj=self,
                audience=get_user_model().objects.filter(id__in=self.group.members).exclude(id=self.creator.pk),
                session_id=session_id,
                end_session=True,
            )
        if not created and self.__state == Poll.STATE_VOTING_OPEN and self.state == Poll.STATE_CLOSED:
            # poll went from open to closed, so maybe send a notification for poll closed?
            # send signal only for voters as audience!
            voter_ids = list(set(self.options.all().values_list('votes__voter__id', flat=True)))
            if self.creator.id in voter_ids:
                voter_ids.remove(self.creator.id)
            voters = get_user_model().objects.filter(id__in=voter_ids)
            cosinnus_notifications.poll_completed.send(
                sender=self, user=self.creator, obj=self, audience=voters, session_id=session_id
            )
            # message following users
            followers_except_creator = [pk for pk in self.get_followed_user_ids() if pk not in [self.creator_id]]
            cosinnus_notifications.following_poll_completed.send(
                sender=self,
                user=self.creator,
                obj=self,
                audience=get_user_model().objects.filter(id__in=followers_except_creator),
                session_id=session_id,
                end_session=True,
            )

        self.__state = self.state

    def get_absolute_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:poll:detail', kwargs=kwargs)

    def get_edit_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:poll:edit', kwargs=kwargs)

    def get_delete_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:poll:delete', kwargs=kwargs)

    def get_options_hash(self):
        """Returns a hashable string containing all suggestions with their time.
        Useful to compare equality of suggestions for two doodles."""
        return ','.join(list(self.options.all().values_list('description', flat=True)))

    def set_winning_option(self, winning_option=None):
        if winning_option is None:
            # No option selected or remove selection
            self.winning_option = None
        elif winning_option.poll.pk == self.pk:
            # Make sure to not assign a option belonging to another poll.
            self.option = winning_option
        else:
            return
        self.save(update_fields=['winning_option'])

    @classmethod
    def get_current(self, group, user):
        """Returns a queryset of the current polls"""
        qs = Poll.objects.filter(group=group)
        if user:
            qs = filter_tagged_object_queryset_for_user(qs, user)
        return current_poll_filter(qs)

    def get_voters_pks(self):
        """Gets the pks of all Users that have voted for this poll.
        Returns an empty list if nobody has voted on the poll."""
        return self.options.all().values_list('votes__voter__id', flat=True).distinct()

    def get_comment_post_url(self):
        return group_aware_reverse('cosinnus:poll:comment', kwargs={'group': self.group, 'poll_slug': self.slug})


@six.python_2_unicode_compatible
class Option(ThumbnailableImageMixin, models.Model):
    image_attr_name = 'image'

    poll = models.ForeignKey(
        Poll,
        verbose_name=_('Poll'),
        on_delete=models.CASCADE,
        related_name='options',
    )

    description = models.TextField(_('Description'), blank=False, null=False)
    image = models.ImageField(_('Image'), upload_to=get_poll_image_filename, blank=True, null=True)

    count = models.PositiveIntegerField(pgettext_lazy('the subject', 'Votes'), default=0, editable=False)

    class Meta(object):
        ordering = ['poll', '-count']
        verbose_name = _('Poll Option')
        verbose_name_plural = _('Poll Options')

    def __str__(self):
        return 'Poll Option for Poll id: %s' % str(getattr(self, 'poll_id', None))

    def get_absolute_url(self):
        return self.poll.get_absolute_url()

    def update_vote_count(self, count=None):
        self.count = self.votes.count()
        self.save(update_fields=['count'])

    @cached_property
    def sorted_votes(self):
        return self.votes.order_by('voter__first_name', 'voter__last_name')

    @cached_property
    def sorted_votes_by_choice(self):
        return self.votes.order_by('-choice')


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

    option = models.ForeignKey(
        Option,
        verbose_name=_('Option'),
        on_delete=models.CASCADE,
        related_name='votes',
    )

    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Voter'),
        on_delete=models.CASCADE,
        related_name='poll_votes',
    )

    choice = models.PositiveSmallIntegerField(_('Vote'), blank=False, null=False, default=VOTE_NO, choices=VOTE_CHOICES)

    class Meta(object):
        unique_together = ('option', 'voter')
        verbose_name = pgettext_lazy('the subject', 'Vote')
        verbose_name_plural = pgettext_lazy('the subject', 'Votes')

    def __str__(self):
        return 'Vote for poll: "%(poll)s" with choice: %(choice)s' % {
            'poll': self.option.poll.title,
            'choice': self.choice,
        }

    def get_absolute_url(self):
        return self.option.poll.get_absolute_url()

    def get_label(self):
        return force_str(dict(self.VOTE_CHOICES)[self.choice])


@six.python_2_unicode_compatible
class Comment(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('Creator'), on_delete=models.PROTECT, related_name='poll_comments'
    )
    created_on = models.DateTimeField(_('Created'), default=now, editable=False)
    last_modified = models.DateTimeField(_('Last modified'), auto_now=True, editable=False)
    poll = models.ForeignKey(Poll, related_name='comments', on_delete=models.CASCADE)
    text = models.TextField(_('Text'))

    class Meta(object):
        ordering = ['created_on']
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __str__(self):
        return 'Comment on “%(poll)s” by %(creator)s' % {
            'poll': self.poll.title,
            'creator': self.creator.get_full_name(),
        }

    def get_icon(self):
        """Returns the font-awesome icon specific to this object type"""
        return 'fa-comment'

    @property
    def parent(self):
        """Returns the parent object of this comment"""
        return self.poll

    def get_notification_hash_id(self):
        """Overrides the item hashing for notification alert hashing, so that
        he parent item is considered as "the same" item, instead of this comment"""
        return self.parent.id

    def get_absolute_url(self):
        if self.pk:
            return '%s#comment-%d' % (self.poll.get_absolute_url(), self.pk)
        return self.poll.get_absolute_url()

    def get_edit_url(self):
        return group_aware_reverse('cosinnus:poll:comment-update', kwargs={'group': self.poll.group, 'pk': self.pk})

    def get_delete_url(self):
        return group_aware_reverse('cosinnus:poll:comment-delete', kwargs={'group': self.poll.group, 'pk': self.pk})

    def is_user_following(self, user):
        """Delegates to parent object"""
        return self.poll.is_user_following(user)

    def save(self, *args, **kwargs):
        created = bool(self.pk) is False
        super(Comment, self).save(*args, **kwargs)
        session_id = uuid1().int
        if created:
            # comment was created, message poll creator
            if not self.poll.creator == self.creator:
                cosinnus_notifications.poll_comment_posted.send(
                    sender=self, user=self.creator, obj=self, audience=[self.poll.creator], session_id=session_id
                )

            # message votees (except comment creator and poll creator) if voting is still open
            votees_except_creator = [
                pk for pk in self.poll.get_voters_pks() if pk not in [self.creator_id, self.poll.creator_id]
            ]
            if votees_except_creator and self.poll.state == Poll.STATE_VOTING_OPEN:
                cosinnus_notifications.voted_poll_comment_posted.send(
                    sender=self,
                    user=self.creator,
                    obj=self,
                    audience=get_user_model().objects.filter(id__in=votees_except_creator),
                    session_id=session_id,
                )

            # message all followers of the poll
            followers_except_creator = [
                pk for pk in self.poll.get_followed_user_ids() if pk not in [self.creator_id, self.poll.creator_id]
            ]
            cosinnus_notifications.following_poll_comment_posted.send(
                sender=self,
                user=self.creator,
                obj=self,
                audience=get_user_model().objects.filter(id__in=followers_except_creator),
                session_id=session_id,
            )

            # message all taggees (except comment creator)
            if self.poll.media_tag and self.poll.media_tag.persons:
                tagged_users_without_self = self.poll.media_tag.persons.exclude(id=self.creator.id)
                if len(tagged_users_without_self) > 0:
                    cosinnus_notifications.tagged_poll_comment_posted.send(
                        sender=self,
                        user=self.creator,
                        obj=self,
                        audience=list(tagged_users_without_self),
                        session_id=session_id,
                    )

            # end notification session
            cosinnus_notifications.tagged_poll_comment_posted.send(
                sender=self, user=self.creator, obj=self, audience=[], session_id=session_id, end_session=True
            )

    @property
    def group(self):
        """Needed by the notifications system"""
        return self.poll.group

    def grant_extra_read_permissions(self, user):
        """Comments inherit their visibility from their commented on parent"""
        return check_object_read_access(self.poll, user)


@receiver(post_delete, sender=Vote)
def post_vote_delete(sender, **kwargs):
    try:
        kwargs['instance'].option.update_vote_count()
    except Option.DoesNotExist:
        pass


@receiver(post_save, sender=Vote)
def post_vote_save(sender, **kwargs):
    kwargs['instance'].option.update_vote_count()


def current_poll_filter(queryset):
    """Filters a queryset of polls for polls are open or closed (but not archived)."""
    return queryset.exclude(state=Poll.STATE_ARCHIVED)


def past_poll_filter(queryset):
    """Filters a queryset of polls for polls that began before today,
    or have an end date before today."""
    return queryset.filter(state=Poll.STATE_ARCHIVED)


if django.VERSION[:2] < (1, 7):
    from cosinnus_poll import cosinnus_app

    cosinnus_app.register()
