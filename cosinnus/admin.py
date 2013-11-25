# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import Group, GroupAdmin as DjangoGroupAdmin, UserAdmin as DjangoUserAdmin

from cosinnus.forms.group import GroupForm
from cosinnus.models.group import GroupAdmin
from cosinnus.models.profile import get_user_profile_model


## group related admin

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


## user / user profile related admin

USER_PROFILE_MODEL = get_user_profile_model()
USER_MODEL = get_user_model()


class UserProfileAdmin(admin.ModelAdmin):
    pass

admin.site.register(get_user_profile_model(), UserProfileAdmin)


class UserProfileInline(admin.StackedInline):
    model = USER_PROFILE_MODEL


class UserAdmin(DjangoUserAdmin):
    inlines = (UserProfileInline,)

admin.site.unregister(USER_MODEL)
admin.site.register(USER_MODEL, UserAdmin)
