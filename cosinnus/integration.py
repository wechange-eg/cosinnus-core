from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_delete, post_save, pre_save
from oauth2_provider.signals import app_authorized

from cosinnus.core import signals
from cosinnus.models import PENDING_STATUS, CosinnusGroupMembership, UserProfile
from cosinnus.models.group import CosinnusBaseGroup
from cosinnus.models.group_extra import CosinnusConference, CosinnusProject, CosinnusSociety


class CosinnusBaseIntegrationHandler:
    """
    Interface for external service integration.
    Provides hook functions for user, group, membership and oath signals.
    """

    # Enable hooks for user integration
    integrate_users = True

    # Enable hooks for group and membership integration
    integrate_groups = True

    # Enable hooks for oauth integration
    integrate_oauth = False

    # Defines which group models are integrated triggering handler for groups and membership signals.
    # Note: When removing a model from this setting all hooks, even for existing groups, stop triggering.
    integrated_group_models = [CosinnusProject, CosinnusSociety]

    # Group types for integrated_group_models populated in init.
    _integrated_group_types = None

    # Changes to these fields of integrated models trigger an update handler.
    integrated_instance_fields = {
        CosinnusProject: ['name'],
        CosinnusSociety: ['name'],
        get_user_model(): ['first_name', 'last_name'],
        UserProfile: [],
    }

    # helper to populate integrated_group_types and active_group_types
    GROUP_TYPES_BY_MODEL = {
        CosinnusSociety: CosinnusBaseGroup.TYPE_SOCIETY,
        CosinnusProject: CosinnusBaseGroup.TYPE_PROJECT,
        CosinnusConference: CosinnusBaseGroup.TYPE_CONFERENCE,
    }

    def __init__(self):
        # init group types
        self._integrated_group_types = [self.GROUP_TYPES_BY_MODEL[model] for model in self.integrated_group_models]

        # user hooks
        # Note: using weak=False as otherwise the function is removed by garbage collection and is not called.
        if self.integrate_users:
            User = get_user_model()
            post_save.connect(self._handle_profile_created, sender=UserProfile, weak=False)
            pre_save.connect(self._handle_user_updated, sender=User, weak=False)
            pre_save.connect(self._handle_profile_updated, sender=UserProfile, weak=False)
            user_logged_in.connect(self._handle_user_logged_in, weak=False)
            signals.user_password_changed.connect(self._handle_user_password_changed, weak=False)
            signals.user_activated.connect(self._handle_user_activated, weak=False)
            signals.user_deactivated.connect(self._handle_user_deactivated, weak=False)
            signals.pre_userprofile_delete.connect(self._handle_profile_deleted, weak=False)
            signals.user_promoted_to_superuser.connect(self._handle_user_promoted_to_superuser, weak=False)
            signals.user_demoted_from_superuser.connect(self._handle_user_demoted_from_superuser, weak=False)

        # group hooks
        if self.integrate_groups:
            for group_model in self.integrated_group_models:
                post_save.connect(self._handle_group_created, sender=group_model, weak=False)
                pre_save.connect(self._handle_group_updated, sender=group_model, weak=False)
                post_delete.connect(self._handle_group_deleted, sender=group_model, weak=False)
                signals.group_reactivated.connect(self._handle_group_activated, sender=group_model, weak=False)
                signals.group_deactivated.connect(self._handle_group_deactivated, sender=group_model, weak=False)

            # membership hooks
            post_save.connect(self._handle_membership_created, sender=CosinnusGroupMembership, weak=False)
            pre_save.connect(self._handle_membership_updated, sender=CosinnusGroupMembership, weak=False)
            post_delete.connect(self._handle_membership_deleted, sender=CosinnusGroupMembership, weak=False)

        # OAuth hooks
        if self.integrate_oauth:
            app_authorized.connect(self._handle_oauth_app_authorized, weak=False)

    def _has_instance_changed(self, instance):
        """Helper to check if a pre-save instance has changed and requires the update handler to be called."""
        instance_model = type(instance)
        old_instance = instance_model.objects.get(pk=instance.pk)
        has_field_changed = any(
            getattr(instance, field) != getattr(old_instance, field)
            for field in self.integrated_instance_fields[instance_model]
        )
        return has_field_changed

    """
    User integration
    """

    def _is_integrated_user(self, user):
        """Checks if a user is considered for integration."""
        return hasattr(user, 'cosinnus_profile') and user.email and not user.is_guest

    def _handle_profile_created(self, sender, instance, created, **kwargs):
        """User create hook."""
        if created and self._is_integrated_user(instance.user):
            self.do_user_create(instance.user)

    def do_user_create(self, user):
        """User create handler."""
        pass  # Implement me

    def _handle_user_updated(self, sender, instance, **kwargs):
        """User update hook."""
        if instance.pk is not None and self._is_integrated_user(instance) and self._has_instance_changed(instance):
            self.do_user_update(instance)

    def _handle_profile_updated(self, sender, instance, **kwargs):
        """Profile update hook."""
        if instance.pk is not None and self._is_integrated_user(instance.user) and self._has_instance_changed(instance):
            self.do_user_update(instance.user)

    def do_user_update(self, user):
        """User update hook. Called for user or profile changes."""
        pass  # Implement me

    def _handle_user_logged_in(self, sender, user, **kwargs):
        """User login hook."""
        if self._is_integrated_user(user):
            self.do_user_login(user)

    def do_user_login(self, user):
        """User login handler."""
        pass  # Implement me

    def _handle_user_password_changed(self, sender, instance, **kwargs):
        """Password changed hook triggering the user logout hook."""
        if self._is_integrated_user(instance):
            self.do_user_logout(instance)

    def do_user_logout(self, user):
        """User logout hook."""
        pass  # Implement me

    def _handle_user_activated(self, sender, user, **kwargs):
        """User (re-)activation hook."""
        if self._is_integrated_user(user):
            self.do_user_activate(user)

    def do_user_activate(self, user):
        """User (re-)activation handler."""
        pass  # Implement me

    def _handle_user_deactivated(self, sender, user, **kwargs):
        """User deactivation hook."""
        if self._is_integrated_user(user):
            self.do_user_deactivate(user)

    def do_user_deactivate(self, user):
        """User deactivation handler."""
        pass  # Implement me

    def _handle_profile_deleted(self, sender, profile, **kwargs):
        """Profile delete hook triggering the user delete handler."""
        if self._is_integrated_user(profile.user):
            self.do_user_delete(profile.user)

    def do_user_delete(self, user):
        """User delete handler."""
        pass  # Implement me

    def _handle_user_promoted_to_superuser(self, sender, user, **kwargs):
        """Hook if a user is made superuser."""
        if self._is_integrated_user(user):
            self.do_user_promote_to_superuser(user)

    def do_user_promote_to_superuser(self, user):
        """User made superuser handler."""
        pass  # Implement me

    def _handle_user_demoted_from_superuser(self, sender, user, **kwargs):
        """Hook if a superuser is made a normal user."""
        if self._is_integrated_user(user):
            self.do_user_demote_from_superuser(user)

    def do_user_demote_from_superuser(self, user):
        """Superuser made user handler."""
        pass  # Implement me

    """
    Groups integration
    """

    def _handle_group_created(self, sender, instance, created, **kwargs):
        """Group create hook."""
        if created:
            self.do_group_create(instance)

    def do_group_create(self, group):
        """Group create handler."""
        pass  # Implement me

    def _handle_group_updated(self, sender, instance, **kwargs):
        """Group update hook."""
        if instance.pk is not None and self._has_instance_changed(instance):
            self.do_group_update(instance)

    def do_group_update(self, group):
        """Group update handler."""
        pass  # Implement me

    def _handle_group_deleted(self, sender, instance, **kwargs):
        """Group delete hook."""
        self.do_group_delete(instance)

    def do_group_delete(self, group):
        """Group delete handler."""
        pass  # Implement me

    def _handle_group_activated(self, sender, group, **kwargs):
        """Group (re-)activation hook."""
        self.do_group_activate(group)

    def do_group_activate(self, group):
        """Group (re-)activation handler."""
        pass  # Implement me

    def _handle_group_deactivated(self, sender, group, **kwargs):
        """Group deactivation hook."""
        self.do_group_deactivate(group)

    def do_group_deactivate(self, group):
        """Group deactivation handler."""
        pass  # Implement me

    def _is_integrated_membership(self, membership):
        """Checks if a group membership is relevant for integration."""
        return (
            self._is_integrated_user(membership.user)
            and membership.group.type in self._integrated_group_types
            and membership.status not in PENDING_STATUS
        )

    def _handle_membership_created(self, sender, instance, created, **kwargs):
        """Membership create hook."""
        if created and self._is_integrated_membership(instance):
            self.do_membership_create(instance)

    def do_membership_create(self, membership):
        """Membership create handler."""
        pass  # Implement me

    def _handle_membership_updated(self, sender, instance, **kwargs):
        """Membership update hook."""
        if instance.pk is not None and self._is_integrated_membership(instance):
            old_instance = CosinnusGroupMembership.objects.get(pk=instance.id)
            user_changed = instance.user_id != old_instance.user_id
            group_changed = instance.group_id != old_instance.group_id
            status_changed = instance.status != old_instance.status
            if user_changed or group_changed:
                self.do_membership_delete(old_instance)
                self.do_membership_create(instance)
            elif status_changed:
                self.do_membership_update(instance)

    def do_membership_update(self, membership):
        """Membership update handler."""
        pass  # Implement me

    def _handle_membership_deleted(self, sender, instance, **kwargs):
        """Membership delete hook."""
        if (
            self._is_integrated_user(instance.user)
            and instance.group.type in self._integrated_group_types
            and instance.status not in PENDING_STATUS
        ):
            self.do_membership_delete(instance)

    def do_membership_delete(self, membership):
        """Membership delete handler."""
        pass  # Implement me

    """
    OAuth integration
    """

    def get_oauth_application_name(self):
        """Returns the oauth application name."""
        raise NotImplementedError

    def _handle_oauth_app_authorized(self, sender, request, token, **kwargs):
        """OAuth authorization hook."""
        if self._is_integrated_user(token.user) and token.application.name == self.get_oauth_application_name():
            self.do_oauth_app_authorize(token)

    def do_oauth_app_authorize(self, token):
        """OAuth authorization handler."""
        pass  # Implement me
