# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from cosinnus.notify.actions import send_notification

from cosinnus_todo.models import TodoEntry
from cosinnus.utils.urls import group_aware_reverse

NOTIFY_MODELS = [TodoEntry]
NOTIFY_POST_SUBSCRIBE_URLS = {
    'todo.TodoEntry': {
        'show': lambda obj, group: obj.get_absolute_url(),
        'list': lambda obj, group: group_aware_reverse('cosinnus:todo:entry-list', kwargs={'group': group}),
    }
}


@receiver(pre_save, sender=TodoEntry, dispatch_uid='todo.TodoEntry.notify_assignment_change_pre_save')
def notify_assignment_change_pre_save(sender, **kwargs):
    """If the assignee of a todo entry has changed, save the old assignee as attribute ``_old_assigned_to``"""
    instance = kwargs.get('instance', None)  # changed TodoEntry
    if instance and instance.pk is not None and instance.assigned_to is not None:
        todo_db = TodoEntry.objects.get(pk=instance.pk)
        if todo_db.assigned_to is not None and todo_db.assigned_to != instance.assigned_to:
            instance._old_assigned_to = todo_db.assigned_to


@receiver(post_save, sender=TodoEntry, dispatch_uid='todo.TodoEntry.notify_assignment_change_post_save')
def notify_assignment_change_post_save(sender, **kwargs):
    """If there was an old assignee (cf. :py:func:`notify_assignment_change_pre_save`), sends an email to him"""
    created = kwargs.get('created', None)
    if not created:  # notify only if the TodoEntry was changed and not created
        instance = kwargs.get('instance', None)  # changed TodoEntry
        if instance and hasattr(instance, '_old_assigned_to'):
            # send email to the previous assignee
            subject = _('Todo "%(todo_name)s" was assigned to %(assignee_name)s') % {
                'todo_name': instance.title,
                'assignee_name': instance.assigned_to.username,
            }
            template = 'todo_assignee_changed'
            data = {
                'old_assignee_name': instance._old_assigned_to.get_full_name(),
                'todo_name': instance.title,
                'assignee_name': instance.assigned_to.username,
            }

            send_notification(instance._old_assigned_to.email, subject, template, data)
