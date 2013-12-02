# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from cosinnus.models.group import CosinnusGroup, GroupAdmin
from cosinnus.models.profile import get_user_profile_model


## group related admin

class GroupAdminAdmin(admin.ModelAdmin):
    list_display = ('group', 'user')
    list_filter = ('group', 'user')

admin.site.register(GroupAdmin, GroupAdminAdmin)


class GroupAdminInline(admin.StackedInline):
    model = GroupAdmin
    extra = 1


class CosinnusGroupAdmin(admin.ModelAdmin):
    inlines = (GroupAdminInline,)
    prepopulated_fields = {'slug': ('name', )}

admin.site.register(CosinnusGroup, CosinnusGroupAdmin)


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
