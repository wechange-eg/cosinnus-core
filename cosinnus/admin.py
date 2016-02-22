# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from cosinnus.models.group import CosinnusGroupMembership,\
    CosinnusPortal, CosinnusPortalMembership,\
    CosinnusGroup, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING,\
    CosinnusPermanentRedirect, MEMBERSHIP_ADMIN
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import AttachedObject, CosinnusTopicCategory
from cosinnus.models.cms import CosinnusMicropage
from cosinnus.models.feedback import CosinnusReportedObject
from cosinnus.utils.dashboard import create_initial_group_widgets
from cosinnus.models.widget import WidgetConfig
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.utils.group import get_cosinnus_group_model


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
    raw_id_fields = ('user',)
    
admin.site.register(CosinnusGroupMembership, MembershipAdmin)


class PermanentRedirectAdmin(SingleDeleteActionMixin, admin.ModelAdmin):
    list_display = ('to_group', 'from_slug', 'from_type', 'from_portal',)
    list_filter = ('from_portal', 'from_slug', 'to_group')
    search_fields = ('to_group__name', )
    
    def queryset(self, request):
        """ For non-admins, only show the routepoints from their caravan """
        qs = super(PermanentRedirectAdmin, self).queryset(request)
        # filter for current portal only, or not
        # qs = qs.filter(from_portal=CosinnusPortal.get_current())
        return qs
    
admin.site.register(CosinnusPermanentRedirect, PermanentRedirectAdmin)


class PortalMembershipAdmin(admin.ModelAdmin):
    list_display = ('group', 'user_email', 'status', 'date',)
    list_filter = ('group', 'user', 'status',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'group__name')
    raw_id_fields = ('user',)

admin.site.register(CosinnusPortalMembership, PortalMembershipAdmin)



""" Unused, because very inefficient with 2000+ users """
class MembershipInline(admin.StackedInline):
    model = CosinnusGroupMembership
    extra = 0


class CosinnusProjectAdmin(SingleDeleteActionMixin, admin.ModelAdmin):
    actions = ['convert_to_society', 'add_members_to_current_portal', 'move_members_to_current_portal']
    list_display = ('name', 'slug', 'portal', 'public', 'is_active',)
    list_filter = ('portal', 'public', 'is_active',)
    search_fields = ('name', )
    prepopulated_fields = {'slug': ('name', )}
    
    def convert_to_society(self, request, queryset):
        """ Converts this CosinnusGroup's type """
        converted_names = []
        slugs = []
        for group in queryset:
            group.type = CosinnusGroup.TYPE_SOCIETY
            # clear parent group if the project had one (societies cannot have parents!)
            group.parent = None
            group.save(allow_type_change=True)
            if group.type == CosinnusGroup.TYPE_SOCIETY:
                converted_names.append(group.name)
                slugs.append(group.slug)
        get_cosinnus_group_model()._clear_cache(slugs=slugs)
                
        # delete and recreate all group widgets (there might be different ones for group than for porject)
        WidgetConfig.objects.filter(group_id=group.pk).delete()
        create_initial_group_widgets(group, group)
        
        message = _('The following Projects were converted to Societies:') + '\n' + ", ".join(converted_names)
        self.message_user(request, message)
    convert_to_society.short_description = _("Convert selected Projects to Societies")
    
    
    def add_members_to_current_portal(self, request, queryset, remove_all_other_memberships=False):
        """ Converts this CosinnusGroup's type """
        member_names = []
        members = []
        
        for group in queryset:
            group.clear_member_cache()
            members.extend(group.members)
        
        members = list(set(members))
        users = get_user_model().objects.filter(id__in=members)
        
        
        if remove_all_other_memberships:
            # delete all other portal memberships because users were supposed to be moved
            CosinnusPortalMembership.objects.filter(user__in=users).delete()
        else:
            # just add them, that means that pending statuses will be removed to be replaced by members statuses in a second
            CosinnusPortalMembership.objects.filter(status=MEMBERSHIP_PENDING, 
                    group=CosinnusPortal.get_current(), user__in=users).delete()
        for user in users:
            membership, created = CosinnusPortalMembership.objects.get_or_create(group=CosinnusPortal.get_current(), user=user, 
                    defaults={'status': MEMBERSHIP_MEMBER})
            # this ensures that join-signals for all members really arrive (for putting new portal members into the Blog, etc)
            post_save.send(sender=CosinnusPortalMembership, instance=membership, created=True)
            member_names.append('%s %s (%s)' % (user.first_name, user.last_name, user.email))
        
        
        message = _('The following Users were added to this portal:') + '\n' + ", ".join(member_names)
        self.message_user(request, message)
    add_members_to_current_portal.short_description = _("Add all members to current Portal")
    
    
    def move_members_to_current_portal(self, request, queryset):
        """ Converts this CosinnusGroup's type """
        self.add_members_to_current_portal(request, queryset, remove_all_other_memberships=True)
        message = _('In addition, the members were removed from all other Portals.')
        self.message_user(request, message)
    move_members_to_current_portal.short_description = _("Move all members to current Portal (removes all other memberships!)")
    
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
        get_cosinnus_group_model()._clear_cache(slugs=slugs)
        
        # delete and recreate all group widgets (there might be different ones for group than for porject)
        WidgetConfig.objects.filter(group_id=group.pk).delete()
        create_initial_group_widgets(group, group)
        
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
    
    def queryset(self, request):
        """ Allow portals to be accessed only by superusers and Portal-Admins """
        qs = super(CosinnusPortalAdmin, self).queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(Q(memberships__user__id=request.user.id) & Q(memberships__status=MEMBERSHIP_ADMIN))
        return qs

admin.site.register(CosinnusPortal, CosinnusPortalAdmin)



class CosinnusMicropageAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'last_edited_by', 'last_edited')

admin.site.register(CosinnusMicropage, CosinnusMicropageAdmin)


class CosinnusReportedObjectAdmin(admin.ModelAdmin):
    list_display = ('text', 'target_object', 'creator', 'created')
    change_form_template = 'admin/cosinnusreportedobject/change_form.html'

admin.site.register(CosinnusReportedObject, CosinnusReportedObjectAdmin)



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

class PortalMembershipInline(admin.TabularInline):
    model = CosinnusPortalMembership
    extra = 0
    
class GroupMembershipInline(admin.TabularInline):
    model = CosinnusGroupMembership
    extra = 0

class UserAdmin(DjangoUserAdmin):
    inlines = (UserProfileInline, PortalMembershipInline)#, GroupMembershipInline)
    actions = ['deactivate_users']
    list_display = ('is_active', 'username', 'email', 'first_name', 'last_name', 'is_staff', )
    
    def deactivate_users(self, request, queryset):
        count = 0
        for user in queryset:
            user.is_active = False
            user.save()
            count += 1
        message = _('%d Users were deactivated successfully.') % count
        self.message_user(request, message)
    deactivate_users.short_description = _('Deactivate users (will keep all all items they created on the site)')
    

admin.site.unregister(USER_MODEL)
admin.site.register(USER_MODEL, UserAdmin)


class CosinnusTopicCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'name_ru', 'name_uk',)

admin.site.register(CosinnusTopicCategory, CosinnusTopicCategoryAdmin)


class BaseTaggableAdminMixin(object):
    """ Base mixin for the common properties for a BaseTaggableObject admin  """
    list_display = ('title', 'group', 'creator', 'created')
    list_filter = ('group', 'group__portal', 'title')
    search_fields = ('title', 'group__title', 'creator__username', 
         'creator__first_name', 'creator__last_name', 'creator__email')

class BaseHierarchicalTaggableAdminMixin(BaseTaggableAdminMixin):
    list_display = list(BaseTaggableAdminMixin.list_display) + ['path',]

## TODO: FIXME: re-enable after 1.8 migration
#class SpamUserModel(USER_MODEL):
#    class Meta:
#        proxy = True
#
#class SpamUserAdmin(UserAdmin):
#
#    def queryset(self, request):
#        """ For non-admins, only show the routepoints from their caravan """
#        qs = super(SpamUserAdmin, self).queryset(request)
#        qs = qs.filter(is_active=True).filter(
#            Q(cosinnus_profile__website__contains='.pl') | \
#            Q(email__contains='bawimy24.net.pl') | \
#            Q(email__contains='oprogressi.com') | \
#            Q(email__contains='email4everyone.com') | \
#            Q(email__contains='zoho.com') | \
#            Q(email__contains='sedam.gq') | \
#            Q(email__contains='o2.pl') | \
#            Q(email__contains='maetzresumeconsulting.com') | \
#            Q(email__contains='verbrechena.eu') | \
#            Q(email__contains='co.pl') \
#        )
#        return qs
#
#admin.site.register(SpamUserModel, SpamUserAdmin)

