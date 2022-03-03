# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from builtins import object
from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

from cosinnus.models import BaseTaggableObjectModel
from cosinnus.utils.functions import unique_aware_slugify,\
    clean_single_line_text

from cosinnus_todo.conf import settings
from cosinnus_todo.managers import TodoEntryManager
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user,\
    check_ug_membership, check_user_superuser, check_object_read_access
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_todo import cosinnus_notifications
from cosinnus import cosinnus_notifications as cosinnus_core_notifications
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from cosinnus.models.tagged import LikeableObjectMixin
from uuid import uuid1

_TODOLIST_ITEM_COUNT = 'cosinnus/todo/itemcount/%d'

PRIORITY_LOW = 1
PRIORITY_MEDIUM = 2
PRIORITY_HIGH = 3

PRIORITY_CHOICES = (
    (PRIORITY_LOW, _('Later')),
    (PRIORITY_MEDIUM, _('Normal')),
    (PRIORITY_HIGH, _('Important')),
)


@six.python_2_unicode_compatible
class TodoEntry(LikeableObjectMixin, BaseTaggableObjectModel):

    SORT_FIELDS_ALIASES = [
        ('title', 'title'),
        ('created', 'created'),
        ('completed_by', 'completed_by'),
        ('priority', 'priority'),
        ('assigned_to', 'assigned_to'),
        ('is_completed', 'is_completed'),
    ]

    due_date = models.DateField(_('Due by'), blank=True, null=True,
        default=None)

    completed_date = models.DateField(_('Completed on'), blank=True,
        null=True, default=None)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Completed by'), blank=True, null=True, default=None,
        on_delete=models.SET_NULL, related_name='completed_todos')
    is_completed = models.BooleanField(default=0)

    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Assigned to'), blank=True, null=True, default=None,
        on_delete=models.SET_NULL, related_name='assigned_todos')
    __assigned_to = None # for pre-save purposes

    priority = models.PositiveIntegerField(_('Priority'),
        choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)

    note = models.TextField(_('Note'), blank=True, null=True)

    todolist = models.ForeignKey('cosinnus_todo.TodoList',
        verbose_name=_('List'), blank=True, null=True, default=None,
        related_name='todos', on_delete=models.CASCADE)

    objects = TodoEntryManager()

    timeline_template = 'cosinnus_todo/v2/dashboard/timeline_item.html'
    
    class Meta(BaseTaggableObjectModel.Meta):
        ordering = ['is_completed', '-completed_date', '-priority', '-due_date']
        verbose_name = _('Todo')
        verbose_name_plural = _('Todos')

    def __init__(self, *args, **kwargs):
        super(TodoEntry, self).__init__(*args, **kwargs)
        self._todolist = getattr(self, 'todolist', None)
        self.__assigned_to = self.assigned_to

    def __str__(self):
        return self.title
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        return 'fa-tasks'

    def save(self, *args, **kwargs):
        self.is_completed = bool(self.completed_date)
        created = bool(self.pk) == False
        super(TodoEntry, self).save(*args, **kwargs)

        if created:
            # todo was created
            cosinnus_notifications.todo_created.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=self.group.members).exclude(id=self.creator.pk))
        if self.__assigned_to != self.assigned_to:
            session_id = uuid1().int
            # assigned to was changed, send to new assignee
            if self.assigned_to and self.assigned_to != self.request.user:
                cosinnus_notifications.assigned_todo_to_user.send(sender=self, user=self.request.user, obj=self, audience=[self.assigned_to], session_id=session_id)
            # send out a notification to all followers for the change
            followers_except_self = [pk for pk in self.get_followed_user_ids() if not pk in [self.request.user.id]]
            followers_except_self = get_user_model().objects.filter(id__in=followers_except_self)
            cosinnus_notifications.following_todo_assignee_changed.send(sender=self, user=self.creator, obj=self, audience=followers_except_self, session_id=session_id, end_session=True)
            
            
        self._clear_cache()
        self._todolist = self.todolist
        self.__assigned_to = self.assigned_to
    
    def on_save_added_tagged_persons(self, set_users):
        """ Called by the taggable form whenever this object is saved and -new- persons
            have been added as tagged! 
            Overriden from BaseTaggableObject. """
        # exclude creator from audience always
        set_users -= set([self.creator])
        cosinnus_core_notifications.user_tagged_in_object.send(sender=self, user=self.creator, 
                obj=self, audience=list(set_users),
                extra={'mail_template':'cosinnus_todo/notifications/user_tagged_in_todo.txt', 'subject_template':'cosinnus_todo/notifications/user_tagged_in_todo_subj.txt'})
            
    
    def get_absolute_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:todo:entry-detail', kwargs=kwargs)
    
    def get_edit_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:todo:entry-edit', kwargs=kwargs)
    
    def get_delete_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:todo:entry-delete', kwargs=kwargs)

    def can_user_assign(self, user):
        """
        Test if a user can assign this object
        """
        if self.creator_id == user.pk:
            return True
        if self.group.is_admin(user):
            return True
        if check_user_superuser(user):
            return True
        return False

    def _clear_cache(self):
        if self.todolist:
            self.todolist._clear_cache()
        if self._todolist:
            self._todolist._clear_cache()

    def delete(self, *args, **kwargs):
        super(TodoEntry, self).delete(*args, **kwargs)
        self._clear_cache()
        
    @classmethod
    def get_current(self, group, user):
        """ Returns a queryset of the current upcoming events """
        qs = TodoEntry.objects.filter(group=group)
        if user:
            qs = filter_tagged_object_queryset_for_user(qs, user)
        return qs.filter(is_completed=False)
    
    def grant_extra_write_permissions(self, user, **kwargs):
        """ An overridable check for whether this object grants certain users write permissions
            even though by general rules that user couldn't write the object.
            
            For todos, users who are assigned this todo can write to it to finish or reassign it.
            
            @param user: The user to check for extra permissions for """
        only_public_fields = False
        fields = kwargs.get('fields', None)
        if fields:
            # if only a change to todo.assigned_to is requested, 
            # we allow that change if the user is a member of the todo's group
            if len(fields) == 1 and 'assigned_to' in fields:
                only_public_fields = check_ug_membership(user, self.group)
            
        return only_public_fields or self.assigned_to == user

    def get_comment_post_url(self):
        return group_aware_reverse('cosinnus:todo:comment', kwargs={'group': self.group, 'todo_slug': self.slug})
    

@six.python_2_unicode_compatible
class TodoList(models.Model):

    title = models.CharField(_('Title'), max_length=255)
    slug = models.SlugField(max_length=55, blank=True)  # human readable part is 50 chars
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL,
        verbose_name=_('Group'), related_name='+', on_delete=models.CASCADE)
    
    GENERAL_TODOLIST_TITLE_IDENTIFIER = '__special__general_todolist__'
    
    class Meta(object):
        ordering = ('title',)
        unique_together = (('group', 'slug'),)

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        sid = transaction.savepoint()
        try:
            self.todos.all().delete()
            super(TodoList, self).delete(*args, **kwargs)
        except:
            transaction.savepoint_rollback(sid)
        else:
            transaction.savepoint_commit(sid)

    def save(self, *args, **kwargs):
        unique_aware_slugify(self, 'title', 'slug', group=self.group)
        self.title = clean_single_line_text(self.title)
        super(TodoList, self).save(*args, **kwargs)
    
    def get_absolute_url(self):
        kwargs = {'group': self.group, 'listslug': self.slug}
        return group_aware_reverse('cosinnus:todo:list-list', kwargs=kwargs)
    
    def get_delete_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:todo:todolist-delete', kwargs=kwargs)
    
    @property
    def filtered_item_count(self):
        if hasattr(self, 'filtered_items'):
            return self.filtered_items.count()
        return self.item_count()
    
    @property
    def item_count(self):
        #count = getattr(self, '_item_count')
        count = cache.get(_TODOLIST_ITEM_COUNT % self.pk)
        if count is None:
            # Hide completed todos
            count = self.todos.exclude(is_completed__exact=True).count()
            cache.set(_TODOLIST_ITEM_COUNT % self.pk, count)
        return count

    def _clear_cache(self):
        cache.delete(_TODOLIST_ITEM_COUNT % self.pk)
        
    def grant_extra_read_permissions(self, user):
        """ Group members may read todolists """
        return check_ug_membership(user, self.group)
    
    def grant_extra_write_permissions(self, user, **kwargs):
        """ Group members may write/delete todolists """
        return check_ug_membership(user, self.group)
    
    def __getitem__(self, key):
        """ Replaces the name of the general todolist with a general title, specific for different languages.
            This modifies dict-lookup, but not instance member access for the title property.
            ``todolist['title']`` --> overridden!
            ``group.title`` --> not overriden!
            ``getattr(self, 'title')`` --> not overridden! """
        value = getattr(self, key, None)
        if key == 'title' and value == self.GENERAL_TODOLIST_TITLE_IDENTIFIER:
            return getattr(settings, 'COSINNUS_TODO_DEFAULT_TODOLIST_TITLE', value)
        return super(TodoList, self).__getitem__(key)
    
    def is_general_list(self):
        return getattr(self, 'title') == self.GENERAL_TODOLIST_TITLE_IDENTIFIER

@six.python_2_unicode_compatible
class Comment(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Creator'), on_delete=models.PROTECT, related_name='todo_comments')
    created_on = models.DateTimeField(_('Created'), default=now, editable=False)
    last_modified = models.DateTimeField(_('Last modified'), auto_now=True, editable=False)
    todo = models.ForeignKey(TodoEntry, related_name='comments', on_delete=models.CASCADE)
    text = models.TextField(_('Text'))

    class Meta(object):
        ordering = ['created_on']
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __str__(self):
        return 'Comment on “%(todo)s” by %(creator)s' % {
            'todo': self.todo.title,
            'creator': self.creator.get_full_name(),
        }
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        return 'fa-comment'
    
    @property
    def parent(self):
        """ Returns the parent object of this comment """
        return self.todo
    
    def get_notification_hash_id(self):
        """ Overrides the item hashing for notification alert hashing, so that
            he parent item is considered as "the same" item, instead of this comment """
        return self.parent.id

    def get_absolute_url(self):
        if self.pk:
            return '%s#comment-%d' % (self.todo.get_absolute_url(), self.pk)
        return self.todo.get_absolute_url()
    
    def get_edit_url(self):
        return group_aware_reverse('cosinnus:todo:comment-update', kwargs={'group': self.todo.group, 'pk': self.pk})

    def get_delete_url(self):
        return group_aware_reverse('cosinnus:todo:comment-delete', kwargs={'group': self.todo.group, 'pk': self.pk})
    
    def is_user_following(self, user):
        """ Delegates to parent object """
        return self.todo.is_user_following(user)
    
    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Comment, self).save(*args, **kwargs)
        if created:
            session_id = uuid1().int
            # comment was created, message todo creator
            if not self.todo.creator == self.creator:
                cosinnus_notifications.todo_comment_posted.send(sender=self, user=self.creator, obj=self, audience=[self.todo.creator], session_id=session_id)
                
            # message assignee
            if self.todo.assigned_to and not self.todo.assigned_to == self.creator:
                cosinnus_notifications.assigned_todo_comment_posted.send(sender=self, user=self.creator, obj=self, audience=[self.todo.assigned_to], session_id=session_id)
            
            # message all followers of the todo
            followers_except_creator = [pk for pk in self.todo.get_followed_user_ids() if not pk in [self.creator_id, self.todo.creator_id]]
            cosinnus_notifications.following_todo_comment_posted.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=followers_except_creator), session_id=session_id)
            
            # message all taggees (except creator)
            if self.todo.media_tag and self.todo.media_tag.persons:
                tagged_users_without_self = self.todo.media_tag.persons.exclude(id=self.creator.id)
                if self.todo.assigned_to:
                    tagged_users_without_self = tagged_users_without_self.exclude(id=self.todo.assigned_to_id)
                if len(tagged_users_without_self) > 0:
                    cosinnus_notifications.tagged_todo_comment_posted.send(sender=self, user=self.creator, obj=self, audience=list(tagged_users_without_self), session_id=session_id)
            
            # end notification session
            cosinnus_notifications.tagged_todo_comment_posted.send(sender=self, user=self.creator, obj=self, audience=[], session_id=session_id, end_session=True)
            
    @property
    def group(self):
        """ Needed by the notifications system """
        return self.todo.group

    def grant_extra_read_permissions(self, user):
        """ Comments inherit their visibility from their commented on parent """
        return check_object_read_access(self.todo, user)

import django
if django.VERSION[:2] < (1, 7):
    from cosinnus_todo import cosinnus_app
    cosinnus_app.register()
