# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from cosinnus.models.group import CosinnusGroupMembership,\
    CosinnusPortal, CosinnusPortalMembership,\
    CosinnusGroup, CosinnusPermanentRedirect, CosinnusUnregisterdUserGroupInvite, RelatedGroups, CosinnusGroupInviteToken
from cosinnus.models.membership import MEMBERSHIP_PENDING, MEMBERSHIP_MEMBER, MEMBERSHIP_ADMIN
from cosinnus.models.profile import get_user_profile_model,\
    GlobalBlacklistedEmail, GlobalUserNotificationSetting
from cosinnus.models.tagged import AttachedObject, CosinnusTopicCategory,\
    get_tag_object_model, BaseTagObject
from cosinnus.models.cms import CosinnusMicropage
from cosinnus.models.feedback import CosinnusReportedObject,\
    CosinnusSentEmailLog, CosinnusFailedLoginRateLimitLog
from cosinnus.utils.dashboard import create_initial_group_widgets
from cosinnus.models.tagged import TagObject
from cosinnus.models.widget import WidgetConfig
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety,\
    CosinnusConference
from cosinnus.utils.group import get_cosinnus_group_model
from django.contrib.auth import login as django_login

from cosinnus.conf import settings
from cosinnus.models.idea import CosinnusIdea
from cosinnus.core import signals
from django import forms
from django.core.exceptions import ValidationError
from cosinnus.models.bbb_room import BBBRoom, BBBRoomVisitStatistics
from cosinnus.models.conference import CosinnusConferenceRoom,\
    CosinnusConferenceSettings
from cosinnus.models.conference import ParticipationManagement, CosinnusConferenceApplication
from cosinnus.models.managed_tags import CosinnusManagedTag,\
    CosinnusManagedTagAssignment, CosinnusManagedTagType
from cosinnus.models.newsletter import Newsletter, GroupsNewsletter
from cosinnus.models.user_import import CosinnusUserImport
from django.contrib.contenttypes.admin import GenericTabularInline,\
    GenericStackedInline
from django_reverse_admin import ReverseModelAdmin
from cosinnus.views.profile import deactivate_user_and_mark_for_deletion,\
    reactivate_user

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
    actions = ['make_admin', 'make_member']
    if settings.COSINNUS_ROCKET_ENABLED:
        actions += ['force_redo_user_room_membership',]
    
    def make_admin(self, request, queryset):
        """ Converts the memberships' statuses """
        queryset.update(status=MEMBERSHIP_ADMIN)
        self.message_user(request, f'Made {len(queryset)} users an Admin', messages.SUCCESS)
    make_admin.short_description = _("Convert memberships to Admin status")
        
    def make_member(self, request, queryset):
        """ Converts the memberships' statuses """
        queryset.update(status=MEMBERSHIP_MEMBER)
        self.message_user(request, f'Made {len(queryset)} users a Member', messages.SUCCESS)
    make_member.short_description = _("Convert memberships to Member status")
    
    if settings.COSINNUS_ROCKET_ENABLED:
        def force_redo_user_room_membership(self, request, queryset):
            count = 0
            from cosinnus_message.rocket_chat import RocketChatConnection
            rocket = RocketChatConnection()
            for membership in queryset:
                rocket.invite_or_kick_for_membership(membership)
                count += 1
            message = _('%d Users\' rocketchat room memberships were re-done.') % count
            self.message_user(request, message)
        force_redo_user_room_membership.short_description = _('Rocket: Fix missing RocketChat room membership for users')
        
admin.site.register(CosinnusGroupMembership, MembershipAdmin)


class UnregisterdUserGroupInviteAdmin(admin.ModelAdmin):
    list_display = ('group', 'email', 'last_modified',)
    list_filter = ('group', )
    search_fields = ('email', 'group__name')
    readonly_fields = ('last_modified',)
    
admin.site.register(CosinnusUnregisterdUserGroupInvite, UnregisterdUserGroupInviteAdmin)


class CosinnusGroupInviteTokenAdminForm(forms.ModelForm):
    """ Case-insensitive unique validation for the token """
    def clean_token(self):
        current_portal = self.cleaned_data['portal'] or CosinnusPortal.get_current()
        other_tokens = CosinnusGroupInviteToken.objects.filter(portal=current_portal, token__iexact=self.cleaned_data["token"])
        if self.instance:
            other_tokens = other_tokens.exclude(pk=self.instance.pk)
        if other_tokens.count() > 0:
            raise ValidationError(_('A token with the same code already exists! Please choose a different string for your token.'))
        return self.cleaned_data["token"]


class CosinnusGroupInviteTokenAdmin(admin.ModelAdmin):
    form = CosinnusGroupInviteTokenAdminForm
    
    list_display = ('token', 'portal', 'is_active', 'title', 'created',)
    list_filter = ('created', 'portal')
    search_fields = ('token', 'title', 'creator__first_name', 'creator__last_name', 'creator__email') 
    readonly_fields = ('created', 'valid_until') # valid_until is unused as of now
    filter_horizontal = ('invite_groups',)

admin.site.register(CosinnusGroupInviteToken, CosinnusGroupInviteTokenAdmin)


class CosinnusConferenceSettingsInline(GenericStackedInline):
    model = CosinnusConferenceSettings
    template = 'cosinnus/admin/conference_setting_help_text_stacked_inline.html'
    extra = 0
    max_num = 1

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
    list_filter = ('group', 'status',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'group__name')
    raw_id_fields = ('user',)
    actions = ['make_admin', 'make_member']
    
    def make_admin(self, request, queryset):
        """ Converts the memberships' statuses """
        queryset.update(status=MEMBERSHIP_ADMIN)
        self.message_user(request, f'Made {len(queryset)} users an Admin', messages.SUCCESS)
    
    make_admin.short_description = _("Convert memberships to Admin status")
        
    def make_member(self, request, queryset):
        """ Converts the memberships' statuses """
        queryset.update(status=MEMBERSHIP_MEMBER)
        self.message_user(request, f'Made {len(queryset)} users a Member', messages.SUCCESS)
        
    make_member.short_description = _("Convert memberships to Member status")

admin.site.register(CosinnusPortalMembership, PortalMembershipAdmin)



""" Unused, because very inefficient with 2000+ users """
class MembershipInline(admin.StackedInline):
    model = CosinnusGroupMembership
    extra = 0


class CosinnusProjectAdmin(admin.ModelAdmin):
    actions = ['convert_to_society', 'convert_to_conference', 'add_members_to_current_portal', 'move_members_to_current_portal',
                'move_groups_to_current_portal', 'move_groups_to_current_portal_and_message_users']
    list_display = ('name', 'slug', 'portal', 'public', 'is_active',)
    list_filter = ('portal', 'public', 'is_active',)
    search_fields = ('name', 'slug', 'id',)
    prepopulated_fields = {'slug': ('name', )}
    readonly_fields = ('created', 'last_modified', 'is_premium_currently', 'attached_objects',)
    raw_id_fields = ('parent',)
    exclude = ('is_conference', 'conference_is_running')
    inlines = [CosinnusConferenceSettingsInline]
    
    ALL_TYPES_CLASSES = [CosinnusProject, CosinnusSociety, CosinnusConference]
    
    def _convert_to_type(self, request, queryset, to_group_type, to_group_klass):
        """ Converts this CosinnusGroup's type """
        converted_names = []
        refused_portal_names = []
        for group in queryset:
            if group.portal_id != CosinnusPortal.get_current().id:
                refused_portal_names.append(group.name)
                continue
            # don't change type to same type
            if group.type == to_group_type:
                continue
            
            # remove haystack index for this group, re-index after
            group.remove_index()
            # swap types
            old_type = group.type
            group.type = to_group_type
            # clear parent group if the project had one (societies cannot have parents!)
            group.parent = None
            group.save(allow_type_change=True)
            if group.type == to_group_type:
                converted_names.append(group.name)
                CosinnusPermanentRedirect.create_for_pattern(group.portal, old_type, group.slug, group)
                if old_type == CosinnusGroup.TYPE_SOCIETY:
                    # all projects that had this group as parent, get set their parent=None and set this as related project
                    # and all of those former child projects are also added as related to this newly-converted project
                    for project in get_cosinnus_group_model().objects.filter(parent=group):
                        project.parent = None
                        project.save(update_fields=['parent'])
                        RelatedGroups.objects.get_or_create(from_group=project, to_group=group)
                        RelatedGroups.objects.get_or_create(from_group=group, to_group=project)
                
            # we beat the cache with a hammer on all class models, to be sure
            for klass in self.ALL_TYPES_CLASSES:
                klass._clear_cache(group=group)
            get_cosinnus_group_model()._clear_cache(group=group)
            CosinnusGroupMembership.clear_member_cache_for_group(group)
            
            # delete and recreate all group widgets (there might be different ones for group than for project)
            WidgetConfig.objects.filter(group_id=group.pk).delete()
            create_initial_group_widgets(group, group)
            
            # re-index haystack for this group after getting a properly classed, fresh object
            group.remove_index()
            group = to_group_klass.objects.get(id=group.id)
            group.update_index()
        
        if converted_names:
            message = _('The following items were converted to %s:') % to_group_klass.get_trans().VERBOSE_NAME_PLURAL + '\n' + ", ".join(converted_names)
            self.message_user(request, message, messages.SUCCESS)
        if refused_portal_names:
            message_error = 'These items could not be converted because they do not belong to this portal:' + '\n' + ", ".join(refused_portal_names)
            self.message_user(request, message_error, messages.ERROR)
    
    def convert_to_project(self, request, queryset):
        self._convert_to_type(request, queryset, CosinnusGroup.TYPE_PROJECT, CosinnusProject)
    convert_to_project.short_description = CosinnusProject.get_trans().CONVERT_ITEMS_TO
        
    def convert_to_society(self, request, queryset):
        self._convert_to_type(request, queryset, CosinnusGroup.TYPE_SOCIETY, CosinnusSociety)
    convert_to_society.short_description = CosinnusSociety.get_trans().CONVERT_ITEMS_TO
    
    def convert_to_conference(self, request, queryset):
        self._convert_to_type(request, queryset, CosinnusGroup.TYPE_CONFERENCE, CosinnusConference)
    convert_to_conference.short_description = CosinnusConference.get_trans().CONVERT_ITEMS_TO
    
    
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
        
        if member_names:
            message = _('The following Users were added to this portal:') + '\n' + ", ".join(member_names)
            self.message_user(request, message)
    add_members_to_current_portal.short_description = _("Add all members to current Portal")
    
    
    def move_groups_to_current_portal(self, request, queryset, message_members=False):
        """ queryset does not have to be a QS, but can also be a list of groups """
        current_portal = CosinnusPortal.get_current()
        # filter groups from this portal
        ignored_groups = [group for group in queryset if group.portal == current_portal]
        if ignored_groups:
            message = 'The following groups were ignored as they were already in this portal:' + '\n' + ", ".join([group.name for group in ignored_groups])
            self.message_user(request, message)
        
        # filter for groups in external portals
        queryset = [group for group in queryset if not group.portal == current_portal]
        
        # add all members of the groups to this portal
        self.add_members_to_current_portal(request, queryset)
        
        # move groups. redirects should be created automatically
        moved_groups = []
        for group in queryset:
            group.portal = current_portal
            group.save()
            moved_groups.append(group)
            
        if moved_groups:
            message = 'The following groups were moved to this portal:' + '\n' + ", ".join([group.name for group in moved_groups])
            self.message_user(request, message)
        else:
            self.message_user(request, 'No groups were moved.')
        
        # message members if wished
        if message_members:
            member_names = []
            members = []
            
            for group in moved_groups:
                # skip messaging for inactive groups
                if not group.is_active:
                    continue
                group.clear_member_cache()
                group_members = group.members
                users = list(get_user_model().objects.filter(id__in=group_members))
                # send signal for this moved group
                signals.group_moved_to_portal.send(sender=request.user, obj=group, user=request.user, audience=users)
                members.extend(users)
            
            members = list(set(members))
            if members:
                for member in members:
                    member_names.append('%s %s (%s)' % (member.first_name, member.last_name, member.email))
                message = 'The following Users were messaged of the moves (depends on their notification settings)' + '\n' + ", ".join(member_names)
                self.message_user(request, message)
        
    move_groups_to_current_portal.short_description = _("Move selected teams to current portal")
    
    
    def move_groups_to_current_portal_and_message_users(self, request, queryset):
        self.move_groups_to_current_portal(request, queryset, message_members=True)
    move_groups_to_current_portal_and_message_users.short_description = _("Move selected teams to current portal and message members")
    
    
    def move_members_to_current_portal(self, request, queryset):
        """ Converts this CosinnusGroup's type """
        self.add_members_to_current_portal(request, queryset, remove_all_other_memberships=True)
        message = _('In addition, the members were removed from all other Portals.')
        self.message_user(request, message)
    move_members_to_current_portal.short_description = _("Move all members to current Portal (removes all other memberships!)")
    
admin.site.register(CosinnusProject, CosinnusProjectAdmin)


class CosinnusSocietyAdmin(CosinnusProjectAdmin):
    
    actions = ['convert_to_project', 'convert_to_conference', 'move_society_and_subprojects_to_portal', 
                'move_society_and_subprojects_to_portal_and_message_users']
    exclude = None
    
    def get_actions(self, request):
        actions = super(CosinnusSocietyAdmin, self).get_actions(request)
        del actions['convert_to_society']
        return actions
    
    def move_society_and_subprojects_to_portal(self, request, queryset, message_members=False):
        groups_and_projects = []
        for group in queryset:
            groups_and_projects.append(group)
            groups_and_projects.extend(group.groups.all())
        groups_and_projects = list(set(groups_and_projects))
        self.move_groups_to_current_portal(request, groups_and_projects, message_members)
    move_society_and_subprojects_to_portal.short_description = _("Move selected groups and their subprojects to current portal")
        
    def move_society_and_subprojects_to_portal_and_message_users(self, request, queryset):
        self.move_society_and_subprojects_to_portal(request, queryset, message_members=True)
    move_society_and_subprojects_to_portal_and_message_users.short_description = _("Move selected groups and their subprojects to current portal and message members")
    
    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("parent", )
        return super(CosinnusSocietyAdmin, self).get_form(request, obj, **kwargs)

admin.site.register(CosinnusSociety, CosinnusSocietyAdmin)


class CosinnusConferenceAdmin(CosinnusProjectAdmin):
    
    actions = ['convert_to_project', 'convert_to_society',]
    exclude = None
    
    def get_actions(self, request):
        actions = super(CosinnusConferenceAdmin, self).get_actions(request)
        del actions['convert_to_conference']
        return actions

admin.site.register(CosinnusConference, CosinnusConferenceAdmin)


class CosinnusPortalAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'site', 'public')
    prepopulated_fields = {'slug': ('name', )}
    readonly_fields = ('saved_infos',) 
    exclude = ('logo_image', 'background_image', 'protocol', 'public', 
               'website', 'description', 'top_color', 'bottom_color',)
    inlines = [CosinnusConferenceSettingsInline]
    
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
    exclude = ('extra_fields',)

admin.site.register(get_user_profile_model(), UserProfileAdmin)


class UserProfileInline(admin.StackedInline):
    model = USER_PROFILE_MODEL
    exclude = ('extra_fields',)

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
    actions = ['deactivate_users', 'reactivate_users', 'export_as_csv', 'log_in_as_user']
    if settings.COSINNUS_ROCKET_ENABLED:
        actions += ['force_sync_rocket_user', 'make_user_rocket_admin', 'force_redo_user_room_memberships',
                    'ensure_user_account_sanity']
    list_display = ('email', 'is_active', 'date_joined', 'has_logged_in', 'tos_accepted', 'username', 'first_name', 'last_name', 'is_staff', )
    list_filter = list(DjangoUserAdmin.list_filter) + [UserHasLoggedInFilter, UserToSAcceptedFilter,]
    
    def has_logged_in(self, obj):
        return bool(obj.last_login is not None)
    has_logged_in.short_description = _('Has Logged In')
    has_logged_in.boolean = True
    
    def tos_accepted(self, obj):
        return bool(obj.cosinnus_profile.settings and obj.cosinnus_profile.settings.get('tos_accepted', False))
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
            deactivate_user_and_mark_for_deletion(user)
            count += 1
        message = _('%(count)d User account(s) were deactivated successfully. They will be deleted after 30 days from now.') % {'count': count}
        self.message_user(request, message)
    deactivate_users.short_description = _('DEACTIVATE user accounts and DELETE them after 30 days')
    
    def reactivate_users(self, request, queryset):
        count = 0
        for user in queryset:
            reactivate_user(user)
            count += 1
        message = _('%(count)d User account(s) were reactivated successfully.') % {'count': count}
        self.message_user(request, message)
    reactivate_users.short_description = _('Reactivate user accounts')
    
    def log_in_as_user(self, request, queryset):
        user = queryset[0]
        user.backend = 'cosinnus.backends.EmailAuthBackend'
        django_login(request, user)
    
    if settings.COSINNUS_ROCKET_ENABLED:
        def force_sync_rocket_user(self, request, queryset):
            count = 0
            from cosinnus_message.rocket_chat import RocketChatConnection, delete_cached_rocket_connection
            rocket = RocketChatConnection()
            for user in queryset:
                rocket.users_update(user, force_user_update=True, update_password=True)
                delete_cached_rocket_connection(user.cosinnus_profile.rocket_username)
                count += 1
            message = _('%d Users were synchronized successfully.') % count
            self.message_user(request, message)
        force_sync_rocket_user.short_description = _('Rocket: Re-synchronize RocketChat user-account connection (will log users out of RocketChat!)')
        
        def make_user_rocket_admin(self, request, queryset):
            count = 0
            from cosinnus_message.rocket_chat import RocketChatConnection
            rocket = RocketChatConnection()
            for user in queryset:
                rocket.rocket.users_update(user_id=rocket.get_user_id(user), roles=['user', 'admin'])
                count += 1
            message = _('%d Users were made RocketChat admins.') % count
            self.message_user(request, message)
        make_user_rocket_admin.short_description = _('Rocket: Make user RocketChat admin')
        
        def ensure_user_account_sanity(self, request, queryset):
            count = 0
            from cosinnus_message.rocket_chat import RocketChatConnection
            rocket = RocketChatConnection()
            for user in queryset:
                rocket.ensure_user_account_sanity(user)
                count += 1
            message = _('%d Users rocketchat accounts were checked.') % count
            self.message_user(request, message)
        ensure_user_account_sanity.short_description = _('Rocket: Repair/create missing users\' rocketchat accounts')
        
        def force_redo_user_room_memberships(self, request, queryset):
            count = 0
            from cosinnus_message.rocket_chat import RocketChatConnection
            rocket = RocketChatConnection()
            for user in queryset:
                rocket.force_redo_user_room_memberships(user)
                count += 1
            message = _('%d Users\' rocketchat room memberships were re-done.') % count
            self.message_user(request, message)
        force_redo_user_room_memberships.short_description = _('Rocket: Fix missing RocketChat room memberships for users')
        

admin.site.unregister(USER_MODEL)
admin.site.register(USER_MODEL, UserAdmin)


class CosinnusTopicCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'name_ru', 'name_uk',)

admin.site.register(CosinnusTopicCategory, CosinnusTopicCategoryAdmin)



class BaseTaggableAdmin(ReverseModelAdmin):
    """ Base mixin for the common properties for a BaseTaggableObject admin  """
    list_display = ['title', 'group', 'creator', 'created']
    list_filter = ['group__portal',]
    search_fields = ['title', 'slug', 'creator__first_name', 'creator__last_name', 'creator__email', 'group__name']
    readonly_fields = ['media_tag', 'attached_objects']
    inlines = []
    raw_id_fields = ['group', 'creator']
    inline_type = 'stacked'
    inline_reverse = [
        ('media_tag', {'fields': [
                'visibility',
                'location',
                'topics',
                'text_topics',
                'bbb_room',
            ]}),
    ]


class BaseHierarchicalTaggableAdmin(BaseTaggableAdmin):
    list_display = BaseTaggableAdmin.list_display + ['path', 'is_container']
    list_filter = BaseTaggableAdmin.list_filter + ['is_container']


class GlobalUserNotificationSettingAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'setting', 'portal',)
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


class TagObjectAdmin(admin.ModelAdmin):
    pass

admin.site.register(TagObject, TagObjectAdmin)


if settings.COSINNUS_IDEAS_ENABLED:
    
    class CosinnusIdeaAdmin(admin.ModelAdmin):
        list_display = ('title', 'created', 'creator', 'portal')
        list_filter = ('created', 'portal')
        search_fields = ('slug', 'title', 'creator__first_name', 'creator__last_name', 'creator__email') 
        readonly_fields = ('created', 'created_groups')
        raw_id_fields = ('creator',)
    
    admin.site.register(CosinnusIdea, CosinnusIdeaAdmin)


def restart_bbb_rooms(modeladmin, request, queryset):
    for bbb_room in queryset.all():
        try:
            bbb_room.restart()
        except:
            pass


restart_bbb_rooms.short_description = _('Restart')


class CosinnusBBBRoomAdmin(admin.ModelAdmin):
    list_display = ('meeting_id', 'name', 'ended', 'portal')
    list_filter = ('ended', 'portal')
    search_fields = ('meeting_id', 'internal_meeting_id', 'name')
    actions = (restart_bbb_rooms, )
admin.site.register(BBBRoom, CosinnusBBBRoomAdmin)


class CosinnusConferenceRoomAdmin(admin.ModelAdmin):
    list_display = ('title', 'id', 'type', 'group', 'sort_index')
    list_filter = ('group', 'group__portal')
    search_fields = ('slug', 'title',)
    inlines = [CosinnusConferenceSettingsInline]

admin.site.register(CosinnusConferenceRoom, CosinnusConferenceRoomAdmin)

class CosinnusParticipationManagementAdmin(admin.ModelAdmin):
    list_display = ('conference', 'application_start', 'application_end')

admin.site.register(ParticipationManagement, CosinnusParticipationManagementAdmin)

class CosinnusConferenceApplicationAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'conference', 'status')
    search_fields = ('conference__name',)

admin.site.register(CosinnusConferenceApplication, CosinnusConferenceApplicationAdmin)

class BBBRoomVisitStatisticsAdmin(admin.ModelAdmin):
    list_display = ('user', 'bbb_room', 'group', 'visit_datetime')
    list_filter = ('bbb_room',)
    search_fields = ('bbb_room__name', 'group__name')
    
admin.site.register(BBBRoomVisitStatistics, BBBRoomVisitStatisticsAdmin)


class CosinnusNewsletterAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sent')

admin.site.register(Newsletter, CosinnusNewsletterAdmin)

class CosinnusGroupNewsletterAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sent')

admin.site.register(GroupsNewsletter, CosinnusGroupNewsletterAdmin)


class CosinnusManagedTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'portal', 'type', 'paired_group')
    list_filter = ('portal', 'type')
    search_fields = ('slug', 'name', 'paired_group__slug', 'paired_group__name')

admin.site.register(CosinnusManagedTag, CosinnusManagedTagAdmin)


class CosinnusManagedTagTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'portal',)
    list_filter = ('portal',)
    search_fields = ('name',)

admin.site.register(CosinnusManagedTagType, CosinnusManagedTagTypeAdmin)

"""
# Disabled for now, unusable and confusing for customers
class CosinnusManagedTagAssignmentAdmin(admin.ModelAdmin):
    list_display = ('managed_tag', 'content_type', 'object_id', 'approved',)
    list_filter = ('managed_tag__portal',)
    search_fields = ('managed_tag__slug', 'managed_tag__name',)

admin.site.register(CosinnusManagedTagAssignment, CosinnusManagedTagAssignmentAdmin)
"""

class CosinnusUserImportAdmin(admin.ModelAdmin):
    list_display = ('state', 'creator', 'last_modified')
    readonly_fields = ('import_data', 'import_report_html')

admin.site.register(CosinnusUserImport, CosinnusUserImportAdmin)


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

