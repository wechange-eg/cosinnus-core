# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from cosinnus.models.group import CosinnusGroupMembership,\
    CosinnusPortal, CosinnusPortalMembership,\
    CosinnusGroup, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING,\
    CosinnusPermanentRedirect, MEMBERSHIP_ADMIN,\
    CosinnusUnregisterdUserGroupInvite, RelatedGroups
from cosinnus.models.profile import get_user_profile_model,\
    GlobalBlacklistedEmail, GlobalUserNotificationSetting
from cosinnus.models.tagged import AttachedObject, CosinnusTopicCategory
from cosinnus.models.cms import CosinnusMicropage
from cosinnus.models.feedback import CosinnusReportedObject,\
    CosinnusSentEmailLog, CosinnusFailedLoginRateLimitLog
from cosinnus.utils.dashboard import create_initial_group_widgets
from cosinnus.models.widget import WidgetConfig
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.utils.group import get_cosinnus_group_model
from django.contrib.auth import login as django_login


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
    list_filter = ('status',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'group__name')
    raw_id_fields = ('user',)
    
admin.site.register(CosinnusGroupMembership, MembershipAdmin)


class UnregisterdUserGroupInviteAdmin(admin.ModelAdmin):
    list_display = ('group', 'email', 'last_modified',)
    list_filter = ('group', )
    search_fields = ('email', 'group__name')
    readonly_fields = ('last_modified',)
    
admin.site.register(CosinnusUnregisterdUserGroupInvite, UnregisterdUserGroupInviteAdmin)



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


class CosinnusProjectAdmin(admin.ModelAdmin):
    actions = ['convert_to_society', 'add_members_to_current_portal', 'move_members_to_current_portal']
    list_display = ('name', 'slug', 'portal', 'public', 'is_active',)
    list_filter = ('portal', 'public', 'is_active',)
    search_fields = ('name', )
    prepopulated_fields = {'slug': ('name', )}
    readonly_fields = ('created',)
    
    def convert_to_society(self, request, queryset):
        """ Converts this CosinnusGroup's type """
        converted_names = []
        refused_portal_names = []
        for group in queryset:
            if group.portal_id != CosinnusPortal.get_current().id:
                refused_portal_names.append(group.name)
                continue
            group.type = CosinnusGroup.TYPE_SOCIETY
            # clear parent group if the project had one (societies cannot have parents!)
            group.parent = None
            group.save(allow_type_change=True)
            if group.type == CosinnusGroup.TYPE_SOCIETY:
                converted_names.append(group.name)
                CosinnusPermanentRedirect.create_for_pattern(group.portal, CosinnusGroup.TYPE_PROJECT, group.slug, group)
                
            # we beat the cache with a hammer on all class models, to be sure
            CosinnusProject._clear_cache(group=group)
            CosinnusSociety._clear_cache(group=group)
            get_cosinnus_group_model()._clear_cache(group=group)
            CosinnusGroupMembership.clear_member_cache_for_group(group)
            
            # delete and recreate all group widgets (there might be different ones for group than for project)
            WidgetConfig.objects.filter(group_id=group.pk).delete()
            create_initial_group_widgets(group, group)
        
        if converted_names:
            message = _('The following Projects were converted to Groups:') + '\n' + ", ".join(converted_names)
            self.message_user(request, message, messages.SUCCESS)
        if refused_portal_names:
            message_error = 'These Projects could not be converted because they do not belong to this portal:' + '\n' + ", ".join(refused_portal_names)
            self.message_user(request, message_error, messages.ERROR)
        
    convert_to_society.short_description = _("Convert selected Projects to Groups")
    
    
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
        refused_portal_names = []
        for group in queryset:
            if group.portal_id != CosinnusPortal.get_current().id:
                refused_portal_names.append(group.name)
                continue
            group.type = CosinnusGroup.TYPE_PROJECT
            group.save(allow_type_change=True)
            if group.type == CosinnusGroup.TYPE_PROJECT:
                converted_names.append(group.name)
                CosinnusPermanentRedirect.create_for_pattern(group.portal, CosinnusGroup.TYPE_SOCIETY, group.slug, group)
                # all projects that had this group as parent, get set their parent=None and set this as related project
                # and all of those former child projects are also added as related to this newly-converted project
                for project in get_cosinnus_group_model().objects.filter(parent=group):
                    project.parent = None
                    project.save(update_fields=['parent'])
                    RelatedGroups.objects.get_or_create(from_group=project, to_group=group)
                    RelatedGroups.objects.get_or_create(from_group=group, to_group=project)
                    
            # we beat the cache with a hammer on all class models, to be sure
            CosinnusProject._clear_cache(group=group)
            CosinnusSociety._clear_cache(group=group)
            get_cosinnus_group_model()._clear_cache(group=group)
            CosinnusGroupMembership.clear_member_cache_for_group(group)
        
            # delete and recreate all group widgets (there might be different ones for group than for porject)
            WidgetConfig.objects.filter(group_id=group.pk).delete()
            create_initial_group_widgets(group, group)
        
        if converted_names:
            message = _('The following Groups were converted to Projects:') + '\n' + ", ".join(converted_names)
            self.message_user(request, message, messages.SUCCESS)
        if refused_portal_names:
            message_error = 'These Groups could not be converted because they do not belong to this portal:' + '\n' + ", ".join(refused_portal_names)
            self.message_user(request, message_error, messages.ERROR)
        
    convert_to_project.short_description = _("Convert selected Groups to Projects")
    
    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("parent", )
        return super(CosinnusSocietyAdmin, self).get_form(request, obj, **kwargs)

admin.site.register(CosinnusSociety, CosinnusSocietyAdmin)


class CosinnusPortalAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'site', 'public')
    prepopulated_fields = {'slug': ('name', )}
    readonly_fields = ('saved_infos',)
    
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
    list_filter = ('creator',)
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


class UserToSAcceptedFilter(admin.SimpleListFilter):
    """ Will show users that have ever logged in (or not) """
    
    title = _('ToS Accepted')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'tosaccepted'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('ToS Accepted')),
            ('no', _('ToS not Accepted')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(cosinnus_profile__settings__contains='tos_accepted')
        if self.value() == 'no':
            return queryset.exclude(cosinnus_profile__settings__contains='tos_accepted')


class UserHasLoggedInFilter(admin.SimpleListFilter):
    """ Will show users that have ever logged in (or not) """
    
    title = _('User Logged In')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'userloggedin'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Logged in before')),
            ('no', _('Never logged in')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(last_login__exact=None)
        if self.value() == 'no':
            return queryset.filter(last_login__exact=None)


class UserAdmin(DjangoUserAdmin):
    inlines = (UserProfileInline, PortalMembershipInline)#, GroupMembershipInline)
    actions = ['deactivate_users', 'export_as_csv', 'log_in_as_user']
    list_display = ('email', 'is_active', 'has_logged_in', 'tos_accepted', 'username', 'first_name', 'last_name', 'is_staff', )
    list_filter = list(DjangoUserAdmin.list_filter) + [UserHasLoggedInFilter, UserToSAcceptedFilter,]
    
    def has_logged_in(self, obj):
        return bool(obj.last_login is not None)
    has_logged_in.short_description = _('Has Logged In')
    has_logged_in.boolean = True
    
    def tos_accepted(self, obj):
        return bool(obj.cosinnus_profile.settings.get('tos_accepted', False))
    tos_accepted.short_description = _('ToS accepted?')
    tos_accepted.boolean = True
    
    def get_actions(self, request):
        """ We never allow users to be deleted, only deactivated! """
        actions = super(UserAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
    
    def has_delete_permission(self, request, obj=None):
        """ We never allow users to be deleted, only deactivated! """
        return False
    
    def deactivate_users(self, request, queryset):
        count = 0
        for user in queryset:
            user.is_active = False
            user.save()
            count += 1
        message = _('%d Users were deactivated successfully.') % count
        self.message_user(request, message)
    deactivate_users.short_description = _('Deactivate users (will keep all all items they created on the site)')
    
    def log_in_as_user(self, request, queryset):
        user = queryset[0]
        user.backend = 'cosinnus.backends.EmailAuthBackend'
        django_login(request, user)
    

admin.site.unregister(USER_MODEL)
admin.site.register(USER_MODEL, UserAdmin)


class CosinnusTopicCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'name_ru', 'name_uk',)

admin.site.register(CosinnusTopicCategory, CosinnusTopicCategoryAdmin)


class BaseTaggableAdminMixin(object):
    """ Base mixin for the common properties for a BaseTaggableObject admin  """
    list_display = ('title', 'group', 'creator', 'created')
    list_filter = ('group__portal',)
    search_fields = ('title', 'slug', )

class BaseHierarchicalTaggableAdminMixin(BaseTaggableAdminMixin):
    list_display = list(BaseTaggableAdminMixin.list_display) + ['path',]


class GlobalUserNotificationSettingAdmin(admin.ModelAdmin):
    list_display = ('user', 'setting', 'portal',)
    list_filter = ('setting', 'portal',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email',) 
    
admin.site.register(GlobalUserNotificationSetting, GlobalUserNotificationSettingAdmin)


class GlobalBlacklistedEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'created', 'portal',)
    search_fields = ('email', 'portal',) 
    
admin.site.register(GlobalBlacklistedEmail, GlobalBlacklistedEmailAdmin)


class CosinnusSentEmailLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'email', 'title', 'portal')
    list_filter = ('date', 'portal')
    search_fields = ('date', 'email', 'title') 
    readonly_fields = ('date',)

admin.site.register(CosinnusSentEmailLog, CosinnusSentEmailLogAdmin)


class CosinnusFailedLoginRateLimitLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'username', 'ip', 'portal')
    list_filter = ('date', 'portal')
    search_fields = ('date', 'username', 'ip',) 
    readonly_fields = ('date',)

admin.site.register(CosinnusFailedLoginRateLimitLog, CosinnusFailedLoginRateLimitLogAdmin)


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

