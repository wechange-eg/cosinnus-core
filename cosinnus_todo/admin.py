# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from cosinnus_todo.models import TodoEntry, TodoList
from cosinnus.admin import BaseTaggableAdmin


class TodoEntryAdmin(BaseTaggableAdmin):
    list_display = BaseTaggableAdmin.list_display + ['priority', 'completed_date', 'assigned_to', 'todolist']
    list_filter = BaseTaggableAdmin.list_filter + ['priority', ]
    search_fields = BaseTaggableAdmin.search_fields + ['note',]


admin.site.register(TodoEntry, TodoEntryAdmin)

admin.site.register(TodoList)
