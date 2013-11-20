# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth.admin import Group, GroupAdmin as DjangoGroupAdmin

from cosinnus.forms.group import GroupForm
from cosinnus.models.group import GroupAdmin


class GroupAdminAdmin(admin.ModelAdmin):
    list_display = ('group', 'user')
    list_filter = ('group', 'user')

admin.site.register(GroupAdmin, GroupAdminAdmin)


class GroupAdminInline(admin.StackedInline):
    model = GroupAdmin
    extra = 1


class GroupAdmin(DjangoGroupAdmin):
    inlines = (GroupAdminInline,)
    form = GroupForm

admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
