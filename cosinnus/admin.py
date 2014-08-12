# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import AttachedObject
from cosinnus.models.organisation import CosinnusOrganisationMembership,\
    CosinnusOrganisation


# group related admin

class MembershipAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'status', 'date',)
    list_filter = ('group', 'user', 'status',)

admin.site.register(CosinnusGroupMembership, MembershipAdmin)


class MembershipInline(admin.StackedInline):
    model = CosinnusGroupMembership
    extra = 0


class CosinnusGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'public',)
    list_filter = ('public',)
    inlines = (MembershipInline,)
    prepopulated_fields = {'slug': ('name', )}

admin.site.register(CosinnusGroup, CosinnusGroupAdmin)


# Organisation related admin

class OrganisationMembershipAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'user', 'status', 'date',)
    list_filter = ('organisation', 'user', 'status',)

admin.site.register(CosinnusOrganisationMembership, OrganisationMembershipAdmin)


class OrganisationMembershipInline(admin.StackedInline):
    model = CosinnusOrganisationMembership
    extra = 0


class CosinnusOrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug',)
    inlines = (OrganisationMembershipInline,)
    prepopulated_fields = {'slug': ('name', )}

admin.site.register(CosinnusOrganisation, CosinnusOrganisationAdmin)



admin.site.register(AttachedObject)


# user / user profile related admin

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
