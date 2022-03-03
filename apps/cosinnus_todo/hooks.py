# -*- coding: utf-8 -*-
from django.dispatch import receiver

from cosinnus.conf import settings
from cosinnus.core.signals import group_object_created
from cosinnus_todo.models import TodoList


@receiver(group_object_created)
def create_initial_group_widgets(sender, group, **kwargs):
    """ For a newly created group, create a default todo list for it """
    
    TodoList.objects.create(
        title=TodoList.GENERAL_TODOLIST_TITLE_IDENTIFIER,
        slug=settings.COSINNUS_TODO_DEFAULT_TODOLIST_SLUG,
        group=group,
    )
    
