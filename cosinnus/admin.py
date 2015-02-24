# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership,\
    CosinnusSociety, CosinnusProject, CosinnusPortal
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import AttachedObject
from cosinnus.models.cms import CosinnusMicropage


# group related admin

class MembershipAdmin(admin.ModelAdmin):
    list_display = ('group', 'user_email', 'status', 'date',)
    list_filter = ('group', 'user', 'status',)

admin.site.register(CosinnusGroupMembership, MembershipAdmin)


class MembershipInline(admin.StackedInline):
    model = CosinnusGroupMembership
    extra = 0

"""
class CosinnusGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'public',)
    list_filter = ('public',)
    prepopulated_fields = {'slug': ('name', )}

admin.site.register(CosinnusGroup, CosinnusGroupAdmin)
"""

class CosinnusProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'portal', 'public',)
    list_filter = ('portal', 'public',)
    prepopulated_fields = {'slug': ('name', )}

admin.site.register(CosinnusProject, CosinnusProjectAdmin)

class CosinnusSocietyAdmin(CosinnusProjectAdmin):
    
    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("parent", )
        return super(CosinnusSocietyAdmin, self).get_form(request, obj, **kwargs)

admin.site.register(CosinnusSociety, CosinnusSocietyAdmin)


class CosinnusPortalAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'site', 'public')
    prepopulated_fields = {'slug': ('name', )}

admin.site.register(CosinnusPortal, CosinnusPortalAdmin)



class CosinnusMicropageAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'last_edited_by', 'last_edited')

admin.site.register(CosinnusMicropage, CosinnusMicropageAdmin)



admin.site.register(AttachedObject)


# user / user profile related admin

USER_PROFILE_MODEL = get_user_profile_model()
USER_MODEL = get_user_model()


class UserProfileAdmin(admin.ModelAdmin):
    readonly_fields = ('settings',)

admin.site.register(get_user_profile_model(), UserProfileAdmin)


class UserProfileInline(admin.StackedInline):
    model = USER_PROFILE_MODEL
    readonly_fields = ('settings',)


class UserAdmin(DjangoUserAdmin):
    inlines = (UserProfileInline,)

admin.site.unregister(USER_MODEL)
admin.site.register(USER_MODEL, UserAdmin)
