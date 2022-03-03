# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import re
import six

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from embed_video.fields import EmbedVideoField

from cosinnus.models.tagged import BaseTaggableObjectModel, LikeableObjectMixin
from django.utils.functional import cached_property
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user,\
    check_object_read_access
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_note import cosinnus_notifications
from django.contrib.auth import get_user_model

import logging
from django.template.defaultfilters import truncatechars
from cosinnus.models.group import CosinnusPortal
from cosinnus.views.mixins.reflected_objects import MixReflectedObjectsMixin
from uuid import uuid1

from cosinnus.models.mixins.translations import TranslateableFieldsModelMixin

logger = logging.getLogger('cosinnus')

FACEBOOK_POST_URL = 'https://www.facebook.com/%s/posts/%s' # %s, %s :  user_id, post_id


class Note(LikeableObjectMixin, TranslateableFieldsModelMixin, BaseTaggableObjectModel):
    
    if settings.COSINNUS_TRANSLATED_FIELDS_ENABLED:
        translateable_fields = ['title', 'text']
    
    EMPTY_TITLE_PLACEHOLDER = '---'
    
    SORT_FIELDS_ALIASES = [
        ('title', 'title'), ('creator', 'creator'), ('created', 'created'),
    ]

    text = models.TextField(_('Text'))
    video = EmbedVideoField(blank=True, null=True)
    facebook_post_id = models.CharField(_('Facebook Share'), max_length=255, null=True, blank=True)
    
    timeline_template = 'cosinnus_note/v2/dashboard/timeline_item.html'

    class Meta(BaseTaggableObjectModel.Meta):
        ordering = ['-created', 'title']
        verbose_name = _('Note Item')
        verbose_name_plural = _('Note Items')

    def __init__(self, *args, **kwargs):
        super(Note, self).__init__(*args, **kwargs)
        self._meta.get_field('creator').verbose_name = _('Author')

    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        
        # take the first youtube url from the textand save it as a video link
        self.video = None
        for url in self.urls:
            if 'youtube.com' in url or 'youtu.be' in url:
                self.video = url
                break
            
        super(Note, self).save(*args, **kwargs)
        if created:
            session_id = uuid1().int
            group_followers_except_creator_ids = [pk for pk in self.group.get_followed_user_ids() if not pk in [self.creator_id]]
            group_followers_except_creator = get_user_model().objects.filter(id__in=group_followers_except_creator_ids)
            cosinnus_notifications.followed_group_note_created.send(sender=self, user=self.creator, obj=self, audience=group_followers_except_creator, session_id=session_id)
            cosinnus_notifications.note_created.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=self.group.members).exclude(id=self.creator.pk), session_id=session_id, end_session=True)
            
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        return 'fa-quote-right'
    
    def get_absolute_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:note:note', kwargs=kwargs)
    
    def get_edit_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:note:update', kwargs=kwargs)
    
    def get_delete_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:note:delete', kwargs=kwargs)
    
    def get_facebook_post_url(self):
        """ If this post has been posted to facebook and its id is known, returns the URL to the facebook post. 
            @return: A string URL to a facebook post or None """
        if self.facebook_post_id:
            try:
                return FACEBOOK_POST_URL % tuple(self.facebook_post_id.split('_'))
            except:
                if settings.DEBUG:
                    raise
        return None
    
    def get_readable_title(self):
        """ Returns either the title if set, or the text of this news post """
        return self.title if not self.title == self.EMPTY_TITLE_PLACEHOLDER else truncatechars(self.text, 40)
    
    @classmethod
    def get_current(self, group, user):
        """ Returns a queryset of the current upcoming events """
        qs = Note.objects.filter(group=group)
        # mix in reflected objects
        if "%s.%s" % (self._meta.app_label, self._meta.model_name) in settings.COSINNUS_REFLECTABLE_OBJECTS:
            mixin = MixReflectedObjectsMixin()
            qs = mixin.mix_queryset(qs, self._meta.model, group)
        if user:
            qs = filter_tagged_object_queryset_for_user(qs, user)
        return qs
    
    @classmethod
    def get_current_for_portal(self):
        """ Returns a queryset of the current Notes for this portal """
        qs = Note.objects.filter(group__portal=CosinnusPortal.get_current())
        return qs
    
    @cached_property
    def video_id(self):
        """ Returns the video id from a URL as such:
        http://www.youtube.com/watch?v=CENF14Iloxw&hq=1
        """
        video = self.video
        if video:
            # remove a single trailing space, that can exist because of markdown, and is never used in an actual URL
            if video.endswith(')'):
                video = video[:-1]
            match = re.search(r'[?&]v=([a-zA-Z0-9-_]+)[^a-zA-Z0-9-_]', video)
            if not match:
                match = re.search(r'youtu.be/([a-zA-Z0-9-_]+)(&|$)', video)
            if match:
                vid = match.groups()[0]
                return vid
        return None

    @property
    def video_thumbnail(self):
        vid = self.video_id
        ret = None
        if vid:
            ret = 'http://img.youtube.com/vi/%s/hqdefault.jpg' % vid
        return ret
    
    @property
    def urls(self):
        """ Returns a list of all URLs contained in the note's text """
        return re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', self.text)
    
    @property
    def short_text(self):
        return truncatechars(self.text, 100)
    
    def get_comment_post_url(self):
        return group_aware_reverse('cosinnus:note:comment', kwargs={'group': self.group, 'note_slug': self.slug})
    

@six.python_2_unicode_compatible
class Comment(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Creator'), on_delete=models.PROTECT)
    created_on = models.DateTimeField(_('Created'), auto_now_add=True, editable=False)
    note = models.ForeignKey(Note, related_name='comments', on_delete=models.CASCADE)
    text = models.TextField(_('Text'))

    class Meta(object):
        ordering = ['created_on']
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __str__(self):
        return 'Comment on “%(note)s” by %(creator)s' % {
            'note': self.note.title,
            'creator': self.creator.get_full_name(),
        }
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        return 'fa-comment'
    
    @property
    def parent(self):
        """ Returns the parent object of this comment """
        return self.note
    
    def get_notification_hash_id(self):
        """ Overrides the item hashing for notification alert hashing, so that
            he parent item is considered as "the same" item, instead of this comment """
        return self.parent.id

    def get_absolute_url(self):
        if self.pk:
            return '%s#comment-%d' % (self.note.get_absolute_url(), self.pk)
        return self.note.get_absolute_url()
        
    def get_edit_url(self):
        return group_aware_reverse('cosinnus:note:comment-update', kwargs={'group': self.note.group, 'pk': self.pk})

    def get_delete_url(self):
        return group_aware_reverse('cosinnus:note:comment-delete', kwargs={'group': self.note.group, 'pk': self.pk})
    
    def is_user_following(self, user):
        """ Delegates to parent object """
        return self.note.is_user_following(user)
    
    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Comment, self).save(*args, **kwargs)
        if created:
            session_id = uuid1().int
            if not self.note.creator == self.creator:
                # comment was created in own post
                cosinnus_notifications.note_comment_posted.send(sender=self, user=self.creator, obj=self, audience=[self.note.creator], session_id=session_id)
                
            # comment was created, for other commenters posts (we skip the post creator because the previous notification precedes)
            try:
                # message all followers of the note
                followers_except_creator = [pk for pk in self.note.get_followed_user_ids() if not pk in [self.creator_id, self.note.creator_id]]
                cosinnus_notifications.following_note_comment_posted.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=followers_except_creator), session_id=session_id)
                
                # notifications for people who also commented on the note of this comment
                commenter_ids = list(set(self.note.comments.exclude(creator__id__in=[self.creator_id, self.note.creator_id]).values_list('creator', flat=True)))
                commenters = get_user_model().objects.filter(id__in=commenter_ids)
                cosinnus_notifications.note_comment_posted_on_commented_post.send(sender=self, user=self.creator, obj=self, audience=commenters, session_id=session_id)
                
                # notification for any members in this group, excepting thos who already commented on the note (because they already received a notification)
                group_members_without_commenters_ids = [member_id for member_id in self.note.group.members if member_id not in [self.creator_id, self.note.creator_id] + commenter_ids]
                all_members = get_user_model().objects.filter(id__in=group_members_without_commenters_ids)
                cosinnus_notifications.note_comment_posted_on_any.send(sender=self, user=self.creator, obj=self, audience=all_members, session_id=session_id, end_session=True)
            except Exception as e:
                logger.error('There was an error in the note_comments_commented notification. See extra', extra={'exc': e})
                
    @property
    def group(self):
        """ Needed by the notifications system """
        return self.note.group
    
    def grant_extra_read_permissions(self, user):
        """ Comments inherit their visibility from their commented on parent """
        return check_object_read_access(self.note, user)

import django
if django.VERSION[:2] < (1, 7):
    from cosinnus_note import cosinnus_app
    cosinnus_app.register()
