# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from annoying.functions import get_object_or_None
from django import forms
from django.contrib import admin, messages
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.contenttypes.admin import GenericStackedInline
from django.core.exceptions import ValidationError
from django.db.models import JSONField, Q
from django.db.models.signals import post_save
from django.utils import translation
from django.utils.crypto import get_random_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_reverse_admin import ReverseModelAdmin

from cosinnus.backends import elastic_threading_disabled
from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.core.registries import attached_object_registry
from cosinnus.forms.widgets import PrettyJSONWidget
from cosinnus.models.cms import CosinnusMicropage
from cosinnus.models.conference import CosinnusConferencePremiumCapacityInfo, CosinnusConferenceSettings
from cosinnus.models.feedback import CosinnusFailedLoginRateLimitLog, CosinnusReportedObject, CosinnusSentEmailLog
from cosinnus.models.group import (
    CosinnusGroup,
    CosinnusGroupInviteToken,
    CosinnusGroupMembership,
    CosinnusPermanentRedirect,
    CosinnusPortal,
    CosinnusPortalMembership,
    CosinnusUnregisterdUserGroupInvite,
    RelatedGroups,
    UserGroupGuestAccess,
)
from cosinnus.models.group_extra import CosinnusConference, CosinnusProject, CosinnusSociety, ensure_group_type
from cosinnus.models.idea import CosinnusIdea
from cosinnus.models.mail import QueuedMassMail
from cosinnus.models.managed_tags import CosinnusManagedTag, CosinnusManagedTagAssignment, CosinnusManagedTagType
from cosinnus.models.membership import MEMBER_STATUS, MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING
from cosinnus.models.newsletter import GroupsNewsletter, Newsletter
from cosinnus.models.profile import (
    GlobalBlacklistedEmail,
    GlobalUserNotificationSetting,
    UserMatchObject,
    get_user_profile_model,
)
from cosinnus.models.storage import TemporaryData
from cosinnus.models.tagged import AttachedObject, CosinnusTopicCategory, TagObject
from cosinnus.models.user_import import CosinnusUserImport
from cosinnus.models.widget import WidgetConfig
from cosinnus.utils.dashboard import create_initial_group_widgets
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.utils.urls import group_aware_reverse


def admin_log_action(user, instance, message):
    """
    Creates an admin history entry for an instance that can be seen in the instances django admin history  view.
    The message is translated into the default platform language set in the LANGUAGE_CODE setting.
    """
    model = type(instance)
    if model == CosinnusGroup:
        # use the proxy group model
        model = ensure_group_type(instance)
    content_type = get_content_type_for_model(model)
    with translation.override(settings.LANGUAGE_CODE):
        LogEntry.objects.log_action(
            user_id=user.id,
            content_type_id=content_type.pk,
            object_id=instance.id,
            object_repr=str(instance),
            action_flag=CHANGE,
            change_message=message,
        )


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
            message = _('1 %(object)s was deleted successfully') % {'object': queryset.model._meta.verbose_name}
        else:
            message = _('%(number)d %(objects)s were deleted successfully') % {
                'number': queryset.count(),
                'objects': queryset.model._meta.verbose_name_plural,
            }
        self.message_user(request, message)

    really_delete_selected.short_description = _('Delete selected entries')


# group related admin


class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        'group',
        'user_email',
        'status',
        'date',
    )
    list_filter = ('status',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'group__name')
    raw_id_fields = ('user',)
    actions = ['make_admin', 'make_member']
    if settings.COSINNUS_ROCKET_ENABLED:
        actions += [
            'force_redo_user_room_membership',
        ]
    if settings.COSINNUS_CLOUD_ENABLED:
        actions += [
            'force_redo_cloud_user_room_membership',
        ]

    def make_admin(self, request, queryset):
        """Converts the memberships' statuses"""
        # manual saving of each item to trigger signal listeners
        for item in queryset:
            item.status = MEMBERSHIP_ADMIN
            item.save()
        self.message_user(request, f'Made {len(queryset)} users an Admin', messages.SUCCESS)

    make_admin.short_description = _('Convert memberships to Admin status')

    def make_member(self, request, queryset):
        """Converts the memberships' statuses"""
        # manual saving of each item to trigger signal listeners
        for item in queryset:
            item.status = MEMBERSHIP_MEMBER
            item.save()
        self.message_user(request, f'Made {len(queryset)} users a Member', messages.SUCCESS)

    make_member.short_description = _('Convert memberships to Member status')

    if settings.COSINNUS_ROCKET_ENABLED:

        def force_redo_user_room_membership(self, request, queryset):
            count = 0
            from cosinnus_message.rocket_chat import RocketChatConnection  # noqa

            rocket = RocketChatConnection()
            for membership in queryset:
                rocket.invite_or_kick_for_membership(membership)
                count += 1
            message = _("%d Users' rocketchat room memberships were re-done.") % count
            self.message_user(request, message)

        force_redo_user_room_membership.short_description = _(
            'Rocket: Fix missing RocketChat room membership for users'
        )

    if settings.COSINNUS_CLOUD_ENABLED:

        def force_redo_cloud_user_room_membership(self, request, queryset):
            count = 0
            from cosinnus_cloud.hooks import user_joined_group_receiver_sub  # noqa

            for membership in queryset:
                if membership.status in MEMBER_STATUS:
                    user_joined_group_receiver_sub(None, membership.user, membership.group)
                    count += 1
            message = _("%d Users' nextcloud folder memberships were re-done.") % count
            self.message_user(request, message)

        force_redo_cloud_user_room_membership.short_description = _(
            'Nextcloud: Fix missing Nextcloud folder membership for users'
        )


admin.site.register(CosinnusGroupMembership, MembershipAdmin)


class UnregisterdUserGroupInviteAdmin(admin.ModelAdmin):
    list_display = (
        'group',
        'email',
        'last_modified',
    )
    list_filter = ('group',)
    search_fields = ('email', 'group__name')
    readonly_fields = ('last_modified',)


admin.site.register(CosinnusUnregisterdUserGroupInvite, UnregisterdUserGroupInviteAdmin)


class CosinnusGroupInviteTokenAdminForm(forms.ModelForm):
    """Case-insensitive unique validation for the token"""

    def clean_token(self):
        current_portal = self.cleaned_data['portal'] or CosinnusPortal.get_current()
        other_tokens = CosinnusGroupInviteToken.objects.filter(
            portal=current_portal, token__iexact=self.cleaned_data['token']
        )
        if self.instance:
            other_tokens = other_tokens.exclude(pk=self.instance.pk)
        if other_tokens.count() > 0:
            raise ValidationError(
                _('A token with the same code already exists! Please choose a different string for your token.')
            )
        return self.cleaned_data['token']


class CosinnusGroupInviteTokenAdmin(admin.ModelAdmin):
    form = CosinnusGroupInviteTokenAdminForm

    list_display = ('token', 'portal', 'is_active', 'title', 'created')
    list_filter = ('created', 'portal')
    search_fields = ('token', 'title', 'invite_groups__name', 'invite_groups__slug')
    readonly_fields = ('created', 'valid_until')  # valid_until is unused as of now
    filter_horizontal = ('invite_groups',)


admin.site.register(CosinnusGroupInviteToken, CosinnusGroupInviteTokenAdmin)


class CosinnusConferenceSettingsInline(GenericStackedInline):
    model = CosinnusConferenceSettings
    template = 'cosinnus/admin/conference_setting_help_text_stacked_inline.html'
    extra = 0
    max_num = 1

    formfield_overrides = {JSONField: {'widget': PrettyJSONWidget(attrs={'style': 'width:initial;'})}}


class PermanentRedirectAdmin(SingleDeleteActionMixin, admin.ModelAdmin):
    list_display = (
        'to_group',
        'from_slug',
        'from_type',
        'from_portal',
    )
    search_fields = (
        'from_slug',
        'from_type',
        'to_group__name',
    )

    def queryset(self, request):
        """For non-admins, only show the routepoints from their caravan"""
        qs = super(PermanentRedirectAdmin, self).queryset(request)
        # filter for current portal only, or not
        # qs = qs.filter(from_portal=CosinnusPortal.get_current())
        return qs


admin.site.register(CosinnusPermanentRedirect, PermanentRedirectAdmin)


class PortalMembershipAdmin(admin.ModelAdmin):
    list_display = (
        'group',
        'user_email',
        'status',
        'date',
    )
    list_filter = (
        'group',
        'status',
    )
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'group__name')
    raw_id_fields = ('user',)
    actions = ['make_admin', 'make_member']

    def make_admin(self, request, queryset):
        """Converts the memberships' statuses"""
        # manual saving of each item to trigger signal listeners
        for item in queryset:
            item.status = MEMBERSHIP_ADMIN
            item.save()
        self.message_user(request, f'Made {len(queryset)} users an Admin', messages.SUCCESS)

    make_admin.short_description = _('Convert memberships to Admin status')

    def make_member(self, request, queryset):
        """Converts the memberships' statuses"""
        # manual saving of each item to trigger signal listeners
        for item in queryset:
            item.status = MEMBERSHIP_MEMBER
            item.save()
        self.message_user(request, f'Made {len(queryset)} users a Member', messages.SUCCESS)

    make_member.short_description = _('Convert memberships to Member status')


admin.site.register(CosinnusPortalMembership, PortalMembershipAdmin)


""" Unused, because very inefficient with 2000+ users """


class MembershipInline(admin.StackedInline):
    model = CosinnusGroupMembership
    extra = 0


class CosinnusProjectAdmin(admin.ModelAdmin):
    actions = [
        'convert_to_society',
        'convert_to_conference',
        'add_members_to_current_portal',
        'move_members_to_current_portal',
        'move_groups_to_current_portal',
        'move_groups_to_current_portal_and_message_users',
        'activate_groups',
        'deactivate_groups',
    ]
    if settings.COSINNUS_CLOUD_ENABLED:
        actions += [
            'force_redo_cloud_user_room_memberships',
        ]
    list_display = (
        'name',
        'slug',
        'portal',
        'public',
        'is_active',
    )
    list_filter = (
        'portal',
        'public',
        'is_active',
    )
    search_fields = (
        'name',
        'slug',
        'id',
    )
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = [
        'created',
        'last_modified',
        'is_premium_currently',
        'attached_objects',
    ]
    raw_id_fields = ('parent',)
    exclude = [
        'is_conference',
    ]
    if settings.COSINNUS_CONFERENCES_ENABLED:
        inlines = [CosinnusConferenceSettingsInline]

    ALL_TYPES_CLASSES = [CosinnusProject, CosinnusSociety, CosinnusConference]

    def _convert_to_type(self, request, queryset, to_group_type, to_group_klass):
        """Converts this CosinnusGroup's type"""
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
                    # all projects that had this group as parent, get set their parent=None and set this as related
                    # project and all of those former child projects are also added as related to this newly-converted
                    # project
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
            converted_typed_group = get_object_or_None(to_group_klass, id=group.id)
            if converted_typed_group:
                converted_typed_group.update_index()
            else:
                message_error = (
                    f'There seems to have been a problem converting: "{group.slug}" from "{type(group)}" to '
                    f'"{to_group_klass}". Please check if it has been converted in the admin. If it has, it may not '
                    f'appear converted until the cache is refreshed. You can do this by saving it in the admin again '
                    f'now.'
                )
                self.message_user(request, message_error, messages.ERROR)

        if converted_names:
            message = (
                _('The following items were converted to %s:') % to_group_klass.get_trans().VERBOSE_NAME_PLURAL
                + '\n'
                + ', '.join(converted_names)
            )
            self.message_user(request, message, messages.SUCCESS)
        if refused_portal_names:
            message_error = (
                'These items could not be converted because they do not belong to this portal:'
                + '\n'
                + ', '.join(refused_portal_names)
            )
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

    def activate_groups(self, request, queryset):
        """Deactivates groups"""
        activated_groups = []
        for group in queryset:
            group.is_active = True
            group.save()
            activated_groups.append(group)
        message = (
            _('The following items were activated:') + '\n' + ', '.join([group.name for group in activated_groups])
        )
        self.message_user(request, message, messages.SUCCESS)

    activate_groups.short_description = CosinnusProject.get_trans().ACTIVATE

    def deactivate_groups(self, request, queryset):
        """Deactivates groups"""
        deactivated_groups = []
        for group in queryset:
            group.is_active = False
            group.save()
            deactivated_groups.append(group)
        message = (
            _('The following items were deactivated:') + '\n' + ', '.join([group.name for group in deactivated_groups])
        )
        self.message_user(request, message, messages.SUCCESS)

    deactivate_groups.short_description = CosinnusProject.get_trans().DEACTIVATE

    def add_members_to_current_portal(self, request, queryset, remove_all_other_memberships=False):
        """Converts this CosinnusGroup's type"""
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
            # just add them, that means that pending statuses will be removed to be replaced by members statuses in a
            # second
            CosinnusPortalMembership.objects.filter(
                status=MEMBERSHIP_PENDING, group=CosinnusPortal.get_current(), user__in=users
            ).delete()
        for user in users:
            membership, __ = CosinnusPortalMembership.objects.get_or_create(
                group=CosinnusPortal.get_current(), user=user, defaults={'status': MEMBERSHIP_MEMBER}
            )
            # this ensures that join-signals for all members really arrive (for putting new portal members into the
            # Blog, etc)
            post_save.send(sender=CosinnusPortalMembership, instance=membership, created=True)
            member_names.append('%s %s (%s)' % (user.first_name, user.last_name, user.email))

        if member_names:
            message = _('The following Users were added to this portal:') + '\n' + ', '.join(member_names)
            self.message_user(request, message)

    add_members_to_current_portal.short_description = _('Add all members to current Portal')

    def move_groups_to_current_portal(self, request, queryset, message_members=False):
        """queryset does not have to be a QS, but can also be a list of groups"""
        current_portal = CosinnusPortal.get_current()
        # filter groups from this portal
        ignored_groups = [group for group in queryset if group.portal == current_portal]
        if ignored_groups:
            message = (
                'The following groups were ignored as they were already in this portal:'
                + '\n'
                + ', '.join([group.name for group in ignored_groups])
            )
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
            message = (
                'The following groups were moved to this portal:'
                + '\n'
                + ', '.join([group.name for group in moved_groups])
            )
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
                message = (
                    'The following Users were messaged of the moves (depends on their notification settings)'
                    + '\n'
                    + ', '.join(member_names)
                )
                self.message_user(request, message)

    move_groups_to_current_portal.short_description = _('Move selected teams to current portal')

    def move_groups_to_current_portal_and_message_users(self, request, queryset):
        self.move_groups_to_current_portal(request, queryset, message_members=True)

    move_groups_to_current_portal_and_message_users.short_description = _(
        'Move selected teams to current portal and message members'
    )

    def move_members_to_current_portal(self, request, queryset):
        """Converts this CosinnusGroup's type"""
        self.add_members_to_current_portal(request, queryset, remove_all_other_memberships=True)
        message = _('In addition, the members were removed from all other Portals.')
        self.message_user(request, message)

    move_members_to_current_portal.short_description = _(
        'Move all members to current Portal (removes all other memberships!)'
    )

    if settings.COSINNUS_CLOUD_ENABLED:

        def force_redo_cloud_user_room_memberships(self, request, queryset):
            count = 0
            from cosinnus_cloud.hooks import user_joined_group_receiver_sub  # noqa

            for group in queryset:
                group_memberships = CosinnusGroupMembership.objects.filter(
                    group__portal=CosinnusPortal.get_current(),
                    group=group,
                    status__in=MEMBER_STATUS,
                )
                for membership in group_memberships:
                    user_joined_group_receiver_sub(None, membership.user, membership.group)
                    count += 1
            message = _("%d Users' nextcloud folder memberships were re-done.") % count
            self.message_user(request, message)

        force_redo_cloud_user_room_memberships.short_description = _(
            'Nextcloud: Fix missing Nextcloud folder membership for users'
        )


admin.site.register(CosinnusProject, CosinnusProjectAdmin)


class CosinnusSocietyAdmin(CosinnusProjectAdmin):
    actions = CosinnusProjectAdmin.actions + [
        'convert_to_project',
        'move_society_and_subprojects_to_portal',
        'move_society_and_subprojects_to_portal_and_message_users',
    ]
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

    move_society_and_subprojects_to_portal.short_description = _(
        'Move selected groups and their subprojects to current portal'
    )

    def move_society_and_subprojects_to_portal_and_message_users(self, request, queryset):
        self.move_society_and_subprojects_to_portal(request, queryset, message_members=True)

    move_society_and_subprojects_to_portal_and_message_users.short_description = _(
        'Move selected groups and their subprojects to current portal and message members'
    )

    def activate_groups(self, request, queryset):
        """Deactivates groups"""
        super(CosinnusSocietyAdmin, self).activate_groups(request, queryset)

    activate_groups.short_description = CosinnusSociety.get_trans().ACTIVATE

    def deactivate_groups(self, request, queryset):
        """Deactivates groups"""
        super(CosinnusSocietyAdmin, self).deactivate_groups(request, queryset)

    deactivate_groups.short_description = CosinnusSociety.get_trans().DEACTIVATE

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ('parent',)
        return super(CosinnusSocietyAdmin, self).get_form(request, obj, **kwargs)


admin.site.register(CosinnusSociety, CosinnusSocietyAdmin)


class CosinnusConferencePremiumCapacityInfoInline(admin.StackedInline):
    model = CosinnusConferencePremiumCapacityInfo
    template = 'cosinnus/admin/conference_premium_capacity_info_help_text_stacked_inline.html'
    extra = 0


class CosinnusPortalAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'site', 'public')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('saved_infos',)
    exclude = (
        'logo_image',
        'background_image',
        'protocol',
        'public',
        'website',
        'description',
        'top_color',
        'bottom_color',
    )
    if settings.COSINNUS_CONFERENCES_ENABLED or settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS:
        inlines = [CosinnusConferenceSettingsInline, CosinnusConferencePremiumCapacityInfoInline]

    def queryset(self, request):
        """Allow portals to be accessed only by superusers and Portal-Admins"""
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


class CosinnusManagedTagAssignmentInline(GenericStackedInline):
    model = CosinnusManagedTagAssignment
    can_delete = True
    extra = 0


class CosinnusUserProfileAdmin(admin.ModelAdmin):
    list_display = ('user',)
    inlines = (CosinnusManagedTagAssignmentInline,)

    def get_model_perms(self, request):
        """Return empty perms dict thus hiding the model from admin index."""
        return {}


admin.site.register(USER_PROFILE_MODEL, CosinnusUserProfileAdmin)


class UserProfileInline(admin.StackedInline):
    model = USER_PROFILE_MODEL
    can_delete = False
    readonly_fields = (
        'deletion_triggered_by_self',
        '_is_guest',
        'guest_access_object',
    )
    show_change_link = True
    view_on_site = False


class PortalMembershipInline(admin.TabularInline):
    model = CosinnusPortalMembership
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class GroupMembershipInline(admin.TabularInline):
    model = CosinnusGroupMembership
    extra = 0
    fields = (
        'group',
        'status',
    )
    readonly_fields = ('group',)

    def has_add_permission(self, request, obj=None):
        return False


class UserToSAcceptedFilter(admin.SimpleListFilter):
    """Will show users that have ever logged in (or not)"""

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
            return queryset.filter(cosinnus_profile__tos_accepted=True)
        if self.value() == 'no':
            return queryset.filter(cosinnus_profile__tos_accepted=False)


class EmailVerifiedFilter(admin.SimpleListFilter):
    """Will show users that have their email verified (or not)"""

    title = _('Email verified')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'emailverified'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Email verified')),
            ('no', _('Email not verified')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(cosinnus_profile__email_verified=True)
        if self.value() == 'no':
            return queryset.exclude(cosinnus_profile__email_verified=True)


class IsGuestFilter(admin.SimpleListFilter):
    """Will show users that have their email verified (or not)"""

    title = _('Is Guest')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'isguest'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Is Guest')),
            ('no', _('Is not a Guest')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(cosinnus_profile___is_guest=True)
        if self.value() == 'no':
            return queryset.exclude(cosinnus_profile___is_guest=True)


class UserHasLoggedInFilter(admin.SimpleListFilter):
    """Will show users that have ever logged in (or not)"""

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


class UserScheduledForDeletionAtFilter(admin.SimpleListFilter):
    """Will show users that have ever logged in (or not)"""

    title = _('Scheduled for Deletion?')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'userscheduledfordeletion'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Yes')),
            ('no', _('No')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(cosinnus_profile__scheduled_for_deletion_at__exact=None)
        if self.value() == 'no':
            return queryset.filter(cosinnus_profile__scheduled_for_deletion_at__exact=None)


_useradmin_excluded_list_filter = ['groups', 'is_staff']


class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (
            _('Personal info'),
            {'fields': ('email', 'first_name', 'last_name', 'username', 'password', 'last_login', 'date_joined')},
        ),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                ),
            },
        ),
    )
    readonly_fields = (
        'last_login',
        'date_joined',
    )
    change_form_template = 'admin/user/change_form.html'
    inlines = (
        UserProfileInline,
        PortalMembershipInline,
        GroupMembershipInline,
    )
    actions = [
        'deactivate_users',
        'reactivate_users',
        'deactivate_spam_users',
        'logout_users',
        'export_as_csv',
        'log_in_as_user',
        'refresh_group_memberships',
    ]
    if settings.COSINNUS_ROCKET_ENABLED:
        actions += [
            'force_sync_rocket_user',
            'make_user_rocket_admin',
            'force_redo_user_room_memberships',
            'ensure_user_account_sanity',
        ]
    if settings.COSINNUS_CLOUD_ENABLED:
        actions += [
            'force_redo_cloud_user_room_memberships',
            'make_user_cloud_admin',
        ]
    list_display = (
        'email',
        'is_active',
        'date_joined',
        'has_logged_in',
        'tos_accepted',
        'email_verified',
        'is_guest',
        'username',
        'first_name',
        'last_name',
        'is_staff',
        'scheduled_for_deletion_at',
    )
    list_filter = [
        field for field in list(DjangoUserAdmin.list_filter) if field not in _useradmin_excluded_list_filter
    ] + [
        'date_joined',
        UserHasLoggedInFilter,
        UserToSAcceptedFilter,
        UserScheduledForDeletionAtFilter,
        EmailVerifiedFilter,
        IsGuestFilter,
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.exclude(email__startswith='__deleted_user__')
        return qs

    def has_logged_in(self, obj):
        return bool(obj.last_login is not None)

    has_logged_in.short_description = _('Has Logged In')
    has_logged_in.boolean = True

    def tos_accepted(self, obj):
        return obj.cosinnus_profile.tos_accepted

    tos_accepted.short_description = _('ToS accepted?')
    tos_accepted.boolean = True

    def email_verified(self, obj):
        return obj.cosinnus_profile.email_verified

    email_verified.short_description = _('Email verified')
    email_verified.boolean = True

    def is_guest(self, obj):
        return obj.is_guest

    is_guest.short_description = _('Is Guest')
    is_guest.boolean = True

    def scheduled_for_deletion_at(self, obj):
        return obj.cosinnus_profile.scheduled_for_deletion_at

    def get_actions(self, request):
        """We never allow users to be deleted, only deactivated!"""
        actions = super(UserAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        """We never allow users to be deleted, only deactivated!"""
        return False

    def deactivate_users(self, request, queryset):
        from cosinnus.views.profile import deactivate_user_and_mark_for_deletion

        count = 0
        for user in queryset:
            if check_user_superuser(user):
                self.message_user(request, 'Skipping deactivating a user that is an admin! Careful who you select!')
                continue
            deactivate_user_and_mark_for_deletion(user)
            count += 1
        message = _(
            '%(count)d User account(s) were deactivated successfully. They will be deleted after 30 days from now.'
        ) % {'count': count}
        self.message_user(request, message)

    deactivate_users.short_description = _('DEACTIVATE user accounts and DELETE them after 30 days')

    def reactivate_users(self, request, queryset):
        from cosinnus.views.profile import reactivate_user

        count = 0
        for user in queryset:
            reactivate_user(user)
            count += 1
        message = _('%(count)d User account(s) were reactivated successfully.') % {'count': count}
        self.message_user(request, message)

    reactivate_users.short_description = _('Reactivate user accounts')

    def deactivate_spam_users(self, request, queryset):
        """For use on spam users that admins want to completely boot off the platform.
        Will deactivate and mark for deletion the user, deactivate all groups they are the only admin of,
        and hide all content from other groups and non-group-content ('visibility: only me')."""
        # TODO: delete this function and replace it with the `get_registered_base_taggable_models`
        #  once the changes from 'dsgvo-deletion' PR are in!
        from django.apps import apps

        from cosinnus.models.tagged import BaseTaggableObjectModel
        from cosinnus.views.profile import deactivate_user_and_mark_for_deletion

        def _get_registered_base_taggable_models():
            base_taggable_object_models = []
            for full_model_name in attached_object_registry:
                app_label, model_name = full_model_name.split('.')
                model = apps.get_model(app_label, model_name)
                if issubclass(model, BaseTaggableObjectModel):
                    base_taggable_object_models.append(model)
            return base_taggable_object_models

        models_to_hide_content = _get_registered_base_taggable_models() + [CosinnusIdea]

        # TODO: move this function to views/profile_deletion.py once the changes from 'dsgvo-deletion' PR are in!
        from cosinnus.models.tagged import BaseTagObject

        def _deactivate_or_hide_all_user_content(user):
            """Deactivate all groups a user is the only admin of,
            and hide all content from other groups and non-group-content ('visibility: only me').
            @return: returns a tuple of ints (num_deactivated_groups, hidden_content)"""
            deactivated_groups = 0
            hidden_content = 0
            for group in CosinnusGroup.objects.get_for_user(user):
                admins = CosinnusGroupMembership.objects.get_admins(group=group)
                if [user.pk] == admins:
                    # user is the only admin of the group, deactivate it
                    group.is_active = False
                    group.save()
                    # remove group from search index
                    group.remove_index()
                    deactivated_groups += 1
            # taggable objects (notes, events, ...) and ideas
            for model_to_hide in models_to_hide_content:
                for object_to_hide in model_to_hide.objects.filter(creator=user):
                    # set visibility to user-only
                    if hasattr(object_to_hide, 'media_tag') and getattr(object_to_hide, 'media_tag', None):
                        media_tag = object_to_hide.media_tag
                        if not media_tag.visibility == BaseTagObject.VISIBILITY_USER:
                            media_tag.visibility = BaseTagObject.VISIBILITY_USER
                            media_tag.save()
                            hidden_content += 1
                        # remove object from search index (always, just to be sure)
                        object_to_hide.remove_index()
            return deactivated_groups, hidden_content

        user_count = 0
        deactivated_groups_count = 0
        hidden_content_count = 0
        for user in queryset:
            if check_user_superuser(user):
                self.message_user(request, 'Skipping banning a user that is an admin! Careful who you select!')
                continue
            _group_count, _hidden_count = _deactivate_or_hide_all_user_content(user)
            with elastic_threading_disabled():
                deactivate_user_and_mark_for_deletion(user)
                if hasattr(user, 'cosinnus_profile') and getattr(user, 'cosinnus_profile', None):
                    profile = user.cosinnus_profile
                    profile.remove_index()
            deactivated_groups_count += _group_count
            hidden_content_count += _hidden_count
            user_count += 1
        message = _(
            '%(user_count)d User account(s) were deactivated successfully. \n'
            '%(deactivated_groups_count)d groups and projects have been deactivated. \n'
            '%(hidden_content_count)d contents have been set invisible. \n'
            'The user(s) will be deleted after 30 days.'
        ) % {
            'user_count': user_count,
            'deactivated_groups_count': deactivated_groups_count,
            'hidden_content_count': hidden_content_count,
        }
        self.message_user(request, message)

    deactivate_spam_users.short_description = _('(SPAM) DEACTIVATE user and their contents (user deletion in 30d)')

    def logout_users(self, request, queryset):
        count = 0
        for user in queryset:
            if hasattr(user, 'cosinnus_profile') and user.cosinnus_profile:
                user.cosinnus_profile.force_logout_user()
                count += 1
        message = _('%(count)d Users were logged out.') % {'count': count}
        self.message_user(request, message)

    logout_users.short_description = _('Logout users')

    def log_in_as_user(self, request, queryset):
        user = queryset[0]
        user.backend = 'cosinnus.backends.EmailAuthBackend'
        django_login(request, user)

    def refresh_group_memberships(self, request, queryset):
        count = 0
        for user in queryset:
            if hasattr(user, 'cosinnus_profile') and user.cosinnus_profile:
                for group in user.cosinnus_profile.cosinnus_groups:
                    CosinnusGroupMembership.objects.get(group=group, user=user).save(force_joined_signal=True)
                count += 1
        message = _("%(count)d Users' group memberships were refreshed.") % {'count': count}
        self.message_user(request, message)

    refresh_group_memberships.short_description = _(
        'Refresh user group membership associations (e.g. cache or Nextcloud folder problems)'
    )

    if settings.COSINNUS_ROCKET_ENABLED:

        def force_sync_rocket_user(self, request, queryset):
            count = 0
            from cosinnus_message.rocket_chat import RocketChatConnection, delete_cached_rocket_connection  # noqa

            rocket = RocketChatConnection()
            for user in queryset:
                rocket.users_update(user, force_user_update=True, update_password=True)
                delete_cached_rocket_connection(user.cosinnus_profile.rocket_username)
                count += 1
            message = _('%d Users were synchronized successfully.') % count
            self.message_user(request, message)

        force_sync_rocket_user.short_description = _(
            'Rocket: Re-synchronize RocketChat user-account connection (will log users out of RocketChat!)'
        )

        def make_user_rocket_admin(self, request, queryset):
            count = 0
            from cosinnus_message.rocket_chat import RocketChatConnection  # noqa

            rocket = RocketChatConnection()
            for user in queryset:
                rocket.rocket.users_update(user_id=rocket.get_user_id(user), roles=['user', 'admin'])
                count += 1
            message = _('%d Users were made RocketChat admins.') % count
            self.message_user(request, message)

        make_user_rocket_admin.short_description = _('Rocket: Make user RocketChat admin')

        def ensure_user_account_sanity(self, request, queryset):
            count = 0
            from cosinnus_message.rocket_chat import RocketChatConnection  # noqa

            rocket = RocketChatConnection()
            for user in queryset:
                rocket.ensure_user_account_sanity(user)
                count += 1
            message = _('%d Users rocketchat accounts were checked.') % count
            self.message_user(request, message)

        ensure_user_account_sanity.short_description = _("Rocket: Repair/create missing users' rocketchat accounts")

        def force_redo_user_room_memberships(self, request, queryset):
            count = 0
            from cosinnus_message.rocket_chat import RocketChatConnection  # noqa

            rocket = RocketChatConnection()
            for user in queryset:
                rocket.force_redo_user_room_memberships(user)
                count += 1
            message = _("%d Users' rocketchat room memberships were re-done.") % count
            self.message_user(request, message)

        force_redo_user_room_memberships.short_description = _(
            'Rocket: Fix missing RocketChat room memberships for users'
        )

    if settings.COSINNUS_CLOUD_ENABLED:

        def force_redo_cloud_user_room_memberships(self, request, queryset):
            count = 0
            from cosinnus_cloud.hooks import user_joined_group_receiver_sub  # noqa

            for user in queryset:
                user_memberships = CosinnusGroupMembership.objects.filter(
                    group__portal=CosinnusPortal.get_current(),
                    user=user,
                    status__in=MEMBER_STATUS,
                )
                for membership in user_memberships:
                    user_joined_group_receiver_sub(None, membership.user, membership.group)
                    count += 1
            message = _("%d Users' nextcloud folder memberships were re-done.") % count
            self.message_user(request, message)

        force_redo_cloud_user_room_memberships.short_description = _(
            'Nextcloud: Fix missing Nextcloud folder membership for users'
        )

        def make_user_cloud_admin(self, request, queryset):
            from cosinnus_cloud.hooks import user_promoted_to_superuser

            count = 0
            for user in queryset:
                user_promoted_to_superuser(None, user)
                count += 1
            message = _('%d Users were made Nextcloud admins.') % count
            self.message_user(request, message)

        make_user_cloud_admin.short_description = _('Nextcloud: Make user Nextcloud admin')


admin.site.unregister(USER_MODEL)
admin.site.register(USER_MODEL, UserAdmin)


class CosinnusTopicCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'name_en',
        'name_ru',
        'name_uk',
    )


admin.site.register(CosinnusTopicCategory, CosinnusTopicCategoryAdmin)


class BaseTaggableAdmin(ReverseModelAdmin):
    """Base mixin for the common properties for a BaseTaggableObject admin"""

    list_display = ['title', 'group', 'creator', 'created']
    list_filter = [
        'group__portal',
    ]
    search_fields = ['title', 'slug', 'creator__first_name', 'creator__last_name', 'creator__email', 'group__name']
    readonly_fields = ['media_tag', 'attached_objects', 'last_action_user', 'group']
    inlines = []
    raw_id_fields = ['group', 'creator']
    inline_type = 'stacked'
    inline_reverse = [
        (
            'media_tag',
            {
                'fields': [
                    'visibility',
                    'location',
                    'topics',
                    'text_topics',
                    'bbb_room',
                ]
            },
        ),
    ]


class BaseHierarchicalTaggableAdmin(BaseTaggableAdmin):
    list_display = BaseTaggableAdmin.list_display + ['path', 'is_container']
    list_filter = BaseTaggableAdmin.list_filter + ['is_container']


class GlobalUserNotificationSettingAdmin(admin.ModelAdmin):
    list_display = (
        'user_email',
        'setting',
        'portal',
    )
    list_filter = (
        'setting',
        'portal',
    )
    search_fields = (
        'user__first_name',
        'user__last_name',
        'user__email',
    )


admin.site.register(GlobalUserNotificationSetting, GlobalUserNotificationSettingAdmin)


class GlobalBlacklistedEmailAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'created',
        'portal',
    )
    search_fields = ('email', 'portal__name')


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
    search_fields = (
        'date',
        'username',
        'ip',
    )
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
    list_display = (
        'name',
        'color',
        'portal',
    )
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
# class SpamUserModel(USER_MODEL):
#    class Meta:
#        proxy = True
#
# class SpamUserAdmin(UserAdmin):
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
# admin.site.register(SpamUserModel, SpamUserAdmin)


if settings.COSINNUS_ENABLE_USER_MATCH:

    class UserMatchAdmin(admin.ModelAdmin):
        def has_change_permission(self, request, obj=None):
            return False

        def has_add_permission(self, request):
            return False

    admin.site.register(UserMatchObject, UserMatchAdmin)


class TemporaryDataAdmin(admin.ModelAdmin):
    fields = ['created', 'deletion_after', 'description']
    list_display = fields

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


admin.site.register(TemporaryData, TemporaryDataAdmin)


class QueuedMassMailAdmin(admin.ModelAdmin):
    fields = [
        'subject',
        'content',
        'recipients_count',
        'recipients_sent_count',
        'created',
        'send_mail_kwargs',
        'sending_in_progress',
    ]
    readonly_fields = ['subject', 'content', 'recipients_count', 'recipients_sent_count', 'created', 'send_mail_kwargs']
    list_display = ['created', 'subject']

    def has_add_permission(self, request):
        return False

    def recipients_count(self, obj):
        return obj.recipients.count()

    recipients_count.short_description = _('Recipients Count')

    def recipients_sent_count(self, obj):
        return obj.recipients_sent.count()

    recipients_sent_count.short_description = _('Recipients Send Count')


admin.site.register(QueuedMassMail, QueuedMassMailAdmin)


if settings.COSINNUS_USER_GUEST_ACCOUNTS_ENABLED:

    class UserGroupGuestAccessAdmin(admin.ModelAdmin):
        list_display = (
            'group',
            'url',
            'creator',
            'token',
            'active_accounts',
        )
        search_fields = ('creator__first_name', 'creator__last_name', 'creator__email', 'group__name', 'token')
        raw_id_fields = ('creator',)

        def active_accounts(self, obj):
            return get_user_profile_model().objects.filter(guest_access_object=obj).count()

        def url(self, obj):
            url = group_aware_reverse('cosinnus:guest-user-signup', kwargs={'guest_token': obj.token})
            url_str = f'<a href="{url}" target="_blank">{url}</a>'
            return mark_safe(url_str)

        def get_changeform_initial_data(self, request):
            return {'token': get_random_string(8, allowed_chars='abcdefghijklmnopqrstuvwxyz').lower()}

        def get_form(self, request, obj=None, **kwargs):
            form = super().get_form(request, obj, **kwargs)
            if obj and obj.pk and obj.token:
                url = group_aware_reverse('cosinnus:guest-user-signup', kwargs={'guest_token': obj.token})
                url_str = f'<a href="{url}" target="_blank">{url}</a>'
                link_text = mark_safe('<br>' + _('Guest access URL') + ': ' + url_str)
                form.base_fields['token'].help_text += link_text
            return form

    admin.site.register(UserGroupGuestAccess, UserGroupGuestAccessAdmin)
