import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from oauth2_provider.signals import app_authorized

from cosinnus.core import signals
from cosinnus.models import (
    CosinnusGroupMembership,
    UserProfile,
)
from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.models.group_extra import CosinnusConference, CosinnusProject, CosinnusSociety
from cosinnus.models.profile import PROFILE_SETTING_ROCKET_CHAT_ID
from cosinnus_event.models import Event
from cosinnus_message import tasks
from cosinnus_message.rocket_chat import (
    ROCKETCHAT_MESSAGE_ID_SETTINGS_KEY,
    RocketChatConnection,
    RocketChatDownException,
)
from cosinnus_note.models import Note

logger = logging.getLogger(__name__)


if settings.COSINNUS_ROCKET_ENABLED:

    def handle_app_authorized(sender, request, token, **kwargs):
        if token.user.is_guest:
            return
        rocket = RocketChatConnection()
        rocket.users_create_or_update(token.user, request=request)

    app_authorized.connect(handle_app_authorized)

    @receiver(pre_save, sender=get_user_model())
    def handle_user_updated(sender, instance, **kwargs):
        # TODO: does this hook trigger correctly?
        # this handles the user update, it is not in post_save!
        if instance.is_guest:
            return
        if instance.id and hasattr(instance, 'cosinnus_profile'):
            old_instance = get_user_model().objects.get(pk=instance.id)
            force = any(
                [
                    getattr(instance, fname) != getattr(old_instance, fname)
                    for fname in ('password', 'first_name', 'last_name', 'email')
                ]
            )
            password_updated = bool(instance.password != old_instance.password)
            tasks.rocket_user_update_task.delay(instance.pk, force, password_updated)

    @receiver(user_logged_in)
    def handle_user_logged_in(sender, user, request, **kwargs):
        """Checks if the user exists in rocketchat, and if not, attempts to create them"""
        if user.is_guest:
            return
        tasks.rocket_user_sanity_task.delay(user.pk)

    @receiver(signals.user_password_changed)
    def handle_user_password_updated(sender, user, **kwargs):
        if user.is_guest:
            return
        tasks.rocket_user_update_task.delay(user.pk, force_update=True, update_password=True)

    @receiver(post_save, sender=UserProfile)
    def handle_profile_updated(sender, instance, created, **kwargs):
        # only update active profiles (inactive ones should be disabled in rocketchat also)
        if not instance.user.is_active:
            return
        if instance.user.is_guest:
            return

        if created:
            # User creation is blocking to avoid concurrency problem with subsequente profile update calls.
            try:
                rocket = RocketChatConnection()
                rocket.users_create(instance.user)
            except RocketChatDownException:
                logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
            except Exception as e:
                logger.exception(e)
        else:
            tasks.rocket_user_update_task.delay(instance.user.pk, force_update=True, update_password=True)

    @receiver(pre_save, sender=CosinnusSociety)
    @receiver(pre_save, sender=CosinnusProject)
    def handle_cosinnus_group_create_missing(sender, instance, **kwargs):
        """Create missing group. TODO: discuss if needed and why."""
        rocket = RocketChatConnection()
        if instance.pk is not None and not rocket.get_group_id(instance, create_if_not_exists=False):
            # Not a threaded call / task as group settings are updated.
            try:
                rocket.groups_create(instance)
            except RocketChatDownException:
                logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
            except Exception as e:
                logger.exception(e)

    @receiver(post_save, sender=CosinnusSociety)
    @receiver(post_save, sender=CosinnusProject)
    def handle_cosinnus_group_updated(sender, instance, created, **kwargs):
        """Creates or updates group channels."""
        tasks.rocket_group_update_task.delay(instance.pk)

    @receiver(post_delete, sender=CosinnusSociety)
    @receiver(post_delete, sender=CosinnusProject)
    @receiver(post_delete, sender=CosinnusConference)
    def handle_cosinnus_group_deleted(sender, instance, **kwargs):
        """Delete group channels."""
        for room_key in settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS:
            key = f'{PROFILE_SETTING_ROCKET_CHAT_ID}_{room_key}'
            room_id = instance.settings.get(key)
            if room_id:
                tasks.rocket_group_room_delete_task.delay(room_id)

    @receiver(signals.group_deactivated)
    def handle_cosinnus_group_deactivated(sender, group, **kwargs):
        """Archive a group that gets deactivated"""
        tasks.rocket_group_archive_task.delay(group.pk)

    @receiver(signals.group_reactivated)
    def handle_cosinnus_group_reactivated(sender, group, **kwargs):
        """Unarchive a group that gets reactivated"""
        tasks.rocket_group_unarchive_task.delay(group.pk)

    @receiver(signals.user_deactivated)
    def user_deactivated(sender, user, **kwargs):
        """Deactivate a rocketchat user account"""
        if user.is_guest:
            return
        tasks.rocket_user_deactivate_task.delay(user.pk)

    @receiver(signals.user_activated)
    def user_activated(sender, user, **kwargs):
        """Activate a rocketchat user account"""
        if user.is_guest:
            return

    @receiver(pre_save, sender=CosinnusGroupMembership)
    def handle_membership_changed(sender, instance, **kwargs):
        """Updates an old RocketChat group membership when group or user are changed."""
        if instance.id:
            old_instance = CosinnusGroupMembership.objects.get(pk=instance.id)
            user_changed = instance.user_id != old_instance.user_id
            group_changed = instance.group_id != old_instance.group_id
            # Invalidate old membership
            if user_changed or group_changed:
                tasks.rocket_group_membership_update_task.delay(old_instance.user.pk, old_instance.group.pk)

    @receiver(post_save, sender=CosinnusGroupMembership)
    def handle_membership_updated(sender, instance, created, **kwargs):
        """Update RocketChat group membership."""
        if instance.user.is_guest:
            return
        tasks.rocket_group_membership_update_task.delay(instance.user.pk, instance.group.pk)

    @receiver(post_delete, sender=CosinnusGroupMembership)
    def handle_membership_deleted(sender, instance, **kwargs):
        """Delete RocketChat group membership."""
        if instance.user.is_guest:
            return
        tasks.rocket_group_membership_update_task.delay(instance.user.pk, instance.group.pk)

    @receiver(post_save, sender=Event)
    @receiver(post_save, sender=Note)
    def handle_relay_message_updated(sender, instance, created, **kwargs):
        if hasattr(instance, 'is_hidden_group_proxy') and instance.is_hidden_group_proxy:
            # Don't relay conference proxy events.
            return
        if created:
            # Not a threaded call as event and note settings are updated.
            # TODO: moved to Celery task. Not sure why this was blocking.
            tasks.rocket_relay_message_create_task.delay(instance._meta.model_name, instance.pk)
        else:
            tasks.rocket_relay_message_update_task.delay(instance._meta.model_name, instance.pk)

    @receiver(post_delete, sender=Event)
    @receiver(post_delete, sender=Note)
    def handle_relay_message_deleted(sender, instance, **kwargs):
        if hasattr(instance, 'is_hidden_group_proxy') and instance.is_hidden_group_proxy:
            # Conference proxy events are not relayed.
            return
        room_key = settings.COSINNUS_ROCKET_NOTE_POST_RELAY_ROOM_KEY
        msg_id = instance.settings.get(ROCKETCHAT_MESSAGE_ID_SETTINGS_KEY)
        if room_key and msg_id:
            tasks.rocket_relay_message_delete_task(instance.group.pk, room_key, msg_id)

    @receiver(signals.pre_userprofile_delete)
    def handle_user_deleted(sender, profile, **kwargs):
        """Called when a user deletes their account. Completely deletes the user's rocket profile"""
        # Not a threaded call as run with management command
        if profile.user.is_guest:
            return
        try:
            rocket = RocketChatConnection()
            rocket.users_delete(profile.user)
        except RocketChatDownException:
            logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
        except Exception as e:
            logger.exception(e)

    @receiver(post_delete, sender=CosinnusConferenceRoom)
    def handle_conference_room_deleted(sender, instance, **kwargs):
        """Called when a conference room is deleted. Delete the corresponding group."""
        if instance.rocket_chat_room_id:
            tasks.rocket_group_room_delete_task.delay(room_id=instance.rocket_chat_room_id)
