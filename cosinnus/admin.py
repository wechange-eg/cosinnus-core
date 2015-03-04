# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import ugettext_lazy as _

from cosinnus.models.group import CosinnusGroupMembership,\
    CosinnusSociety, CosinnusProject, CosinnusPortal, CosinnusPortalMembership,\
    CosinnusGroup
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import AttachedObject
from cosinnus.models.cms import CosinnusMicropage


class SingleDeleteActionMixin(object):
    
    def get_actions(self, request):
        self.actions.append('really_delete_selected')
        actions = super(SingleDeleteActionMixin, self).get_actions(request)
        del actions['delete_selected']
        return actions
    
    def really_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.delete()
        if queryset.count() == 1:
            message = _("1 %(object)s was deleted successfully") % \
                {'object': queryset.model._meta.verbose_name}
        else:
            message = _("%(number)d %(objects)s were deleted successfully") %  \
                {'number': queryset.count(), 'objects': queryset.model._meta.verbose_name_plural}
        self.message_user(request, message)
    really_delete_selected.short_description = _("Delete selected entries")



# group related admin

class MembershipAdmin(admin.ModelAdmin):
    list_display = ('group', 'user_email', 'status', 'date',)
    list_filter = ('group', 'user', 'status',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'group__name')
    
admin.site.register(CosinnusGroupMembership, MembershipAdmin)



class PortalMembershipAdmin(admin.ModelAdmin):
    list_display = ('group', 'user_email', 'status', 'date',)
    list_filter = ('group', 'user', 'status',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'group__name')

admin.site.register(CosinnusPortalMembership, PortalMembershipAdmin)



""" Unused, because very inefficient with 2000+ users """
class MembershipInline(admin.StackedInline):
    model = CosinnusGroupMembership
    extra = 0


class CosinnusProjectAdmin(SingleDeleteActionMixin, admin.ModelAdmin):
    actions = ['convert_to_society']
    list_display = ('name', 'slug', 'portal', 'public',)
    list_filter = ('portal', 'public',)
    search_fields = ('name', )
    prepopulated_fields = {'slug': ('name', )}
    
    def convert_to_society(self, request, queryset):
        """ Converts this CosinnusGroup's type """
        converted_names = []
        slugs = []
        for group in queryset:
            group.type = CosinnusGroup.TYPE_SOCIETY
            group.save(allow_type_change=True)
            if group.type == CosinnusGroup.TYPE_SOCIETY:
                converted_names.append(group.name)
                slugs.append(group.slug)
        CosinnusGroup._clear_cache(slugs=slugs)
        message = _('The following Projects were converted to Societies:') + '\n' + ", ".join(converted_names)
        self.message_user(request, message)
    convert_to_society.short_description = _("Convert selected Projects to Societies")
    
admin.site.register(CosinnusProject, CosinnusProjectAdmin)


class CosinnusSocietyAdmin(CosinnusProjectAdmin):
    
    actions = ['convert_to_project']
    
    def get_actions(self, request):
        actions = super(CosinnusSocietyAdmin, self).get_actions(request)
        del actions['convert_to_society']
        return actions
    
    def convert_to_project(self, request, queryset):
        """ Converts this CosinnusGroup's type """
        converted_names = []
        slugs = []
        for group in queryset:
            group.type = CosinnusGroup.TYPE_PROJECT
            group.save(allow_type_change=True)
            if group.type == CosinnusGroup.TYPE_PROJECT:
                converted_names.append(group.name)
                slugs.append(group.slug)
        CosinnusGroup._clear_cache(slugs=slugs)
        message = _('The following Societies were converted to Projects:') + '\n' + ", ".join(converted_names)
        self.message_user(request, message)
    convert_to_project.short_description = _("Convert selected Societies to Projects")
    
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
