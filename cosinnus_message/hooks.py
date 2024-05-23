import logging
from threading import Thread

from annoying.functions import get_object_or_None
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models import prefetch_related_objects
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
from cosinnus_event.models import Event
from cosinnus_message.rocket_chat import RocketChatConnection, RocketChatDownException, delete_cached_rocket_connection
from cosinnus_message.tasks import rocket_group_membership_update_task
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

            # do a threaded call
            class CosinnusRocketUpdateThread(Thread):
                def run(self):
                    try:
                        rocket = RocketChatConnection()
                        rocket.users_update(instance, force_user_update=force, update_password=password_updated)
                    except RocketChatDownException:
                        logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                    except Exception as e:
                        logger.exception(e)

            CosinnusRocketUpdateThread().start()

    @receiver(user_logged_in)
    def handle_user_logged_in(sender, user, request, **kwargs):
        """Checks if the user exists in rocketchat, and if not, attempts to create them"""
        # we're Threading this entire hook as it might take a while
        if user.is_guest:
            return

        class UserSanityCheck(Thread):
            def run(self):
                try:
                    rocket = RocketChatConnection()
                    rocket.ensure_user_account_sanity(user)
                except RocketChatDownException:
                    logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                except Exception as e:
                    logger.exception(e)

        UserSanityCheck().start()

    @receiver(signals.user_password_changed)
    def handle_user_password_updated(sender, user, **kwargs):
        if user.is_guest:
            return
        # prefetch related objects and do a threaded call
        prefetch_related_objects([user], 'cosinnus_profile')

        class CosinnusRocketPasswordUpdateThread(Thread):
            def run(self):
                try:
                    rocket = RocketChatConnection()
                    rocket.users_update(user, force_user_update=True, update_password=True)
                    delete_cached_rocket_connection(user.cosinnus_profile.rocket_username)
                except RocketChatDownException:
                    logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                except Exception as e:
                    logger.exception(e)

        CosinnusRocketPasswordUpdateThread().start()

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
            # prefetch related objects and do a threaded call
            prefetch_related_objects([instance.user], 'cosinnus_profile')

            class CosinnusRocketProfileUpdateThread(Thread):
                def run(self):
                    try:
                        rocket = RocketChatConnection()
                        rocket.users_update(instance.user)
                    except RocketChatDownException:
                        logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                    except Exception as e:
                        logger.exception(e)

            CosinnusRocketProfileUpdateThread().start()

    @receiver(pre_save, sender=CosinnusSociety)
    @receiver(pre_save, sender=CosinnusProject)
    def handle_cosinnus_group_updated(sender, instance, **kwargs):
        old_instance = get_object_or_None(type(instance), pk=instance.id) if instance.id else None
        try:
            rocket = RocketChatConnection()
            if old_instance:
                if rocket.get_group_id(instance, create_if_not_exists=False):
                    if instance.slug != old_instance.slug:
                        # do a threaded call
                        class CosinnusRocketGroupUpdateThread(Thread):
                            def run(self):
                                try:
                                    rocket.groups_rename(instance)
                                except RocketChatDownException:
                                    logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                                except Exception as e:
                                    logger.exception(e)

                        CosinnusRocketGroupUpdateThread().start()
                else:
                    # Not a threaded call as group settings are updated
                    rocket.groups_create(instance)
        except RocketChatDownException:
            logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
        except Exception as e:
            logger.exception(e)

    @receiver(post_save, sender=CosinnusSociety)
    @receiver(post_save, sender=CosinnusProject)
    def handle_cosinnus_group_created(sender, instance, created, **kwargs):
        if created:
            try:
                # Not a threaded call as group settings are updated
                rocket = RocketChatConnection()
                rocket.groups_create(instance)
            except RocketChatDownException:
                logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
            except Exception as e:
                logger.exception(e)

    def _group_is_conference_without_default_channel(rocket, group):
        """
        Helper to check if group is a conference without a default channel. We disabled default channel creation for
        conferences but still need to handle conferences created before this that still have a default channel.
        """
        if group.group_is_conference:
            default_room_id = rocket.get_group_id(group, create_if_not_exists=False)
            if not default_room_id:
                return True
        return False

    @receiver(post_delete, sender=CosinnusSociety)
    @receiver(post_delete, sender=CosinnusProject)
    @receiver(post_delete, sender=CosinnusConference)
    def handle_cosinnus_group_deleted(sender, instance, **kwargs):
        # do a threaded call
        class CosinnusRocketGroupDeleteThread(Thread):
            def run(self):
                try:
                    rocket = RocketChatConnection()
                    # Check if a default channel exists for a conference. If not there is nothing to be done.
                    if _group_is_conference_without_default_channel(rocket, instance):
                        return
                    rocket.groups_delete(instance)
                except RocketChatDownException:
                    logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                except Exception as e:
                    logger.exception(e)

        CosinnusRocketGroupDeleteThread().start()

    @receiver(signals.group_deactivated)
    def handle_cosinnus_group_deactivated(sender, group, **kwargs):
        """Archive a group that gets deactivated"""
        specific_room_ids = None
        if group.group_is_conference:
            # Deactivate workshop rooms for conference groups.
            specific_room_ids = [room.rocket_chat_room_id for room in group.rooms.all() if room.rocket_chat_room_name]

        # do a threaded call
        class CosinnusRocketGroupDeactivateThread(Thread):
            def run(self):
                try:
                    rocket = RocketChatConnection()
                    if group.group_is_conference:
                        # Deactivate default room, if exists.
                        default_room_id = rocket.get_group_id(group, create_if_not_exists=False)
                        if default_room_id:
                            specific_room_ids.append(default_room_id)
                    rocket.groups_archive(group, specific_room_ids=specific_room_ids)
                except RocketChatDownException:
                    logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                except Exception as e:
                    logger.exception(e)

        CosinnusRocketGroupDeactivateThread().start()

    @receiver(signals.group_reactivated)
    def handle_cosinnus_group_reactivated(sender, group, **kwargs):
        """Unarchive a group that gets reactivated"""
        specific_room_ids = None
        if group.group_is_conference:
            # Reactivate workshop rooms for conferences.
            specific_room_ids = [room.rocket_chat_room_id for room in group.rooms.all() if room.rocket_chat_room_name]

        # do a threaded call
        class CosinnusRocketGroupReactivateThread(Thread):
            def run(self):
                try:
                    rocket = RocketChatConnection()
                    if group.group_is_conference:
                        # Deactivate default room, if exists.
                        default_room_id = rocket.get_group_id(group, create_if_not_exists=False)
                        if default_room_id:
                            specific_room_ids.append(default_room_id)
                    rocket.groups_unarchive(group, specific_room_ids=specific_room_ids)
                except RocketChatDownException:
                    logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                except Exception as e:
                    logger.exception(e)

        CosinnusRocketGroupReactivateThread().start()

    @receiver(signals.user_deactivated)
    def user_deactivated(sender, user, **kwargs):
        """Deactivate a rocketchat user account"""
        if user.is_guest:
            return
        # prefetch related objects and do a threaded call
        prefetch_related_objects([user], 'cosinnus_profile')

        class CosinnusRocketUserDeactivateThread(Thread):
            def run(self):
                try:
                    rocket = RocketChatConnection()
                    rocket.users_disable(user)
                except RocketChatDownException:
                    logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                except Exception as e:
                    logger.exception(e)

        CosinnusRocketUserDeactivateThread().start()

    @receiver(signals.user_activated)
    def user_activated(sender, user, **kwargs):
        """Activate a rocketchat user account"""
        if user.is_guest:
            return
        # prefetch related objects and do a threaded call
        prefetch_related_objects([user], 'cosinnus_profile')

        class CosinnusRocketUserActivateThread(Thread):
            def run(self):
                try:
                    rocket = RocketChatConnection()
                    rocket.users_enable(user)
                except RocketChatDownException:
                    logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                except Exception as e:
                    logger.exception(e)

        CosinnusRocketUserActivateThread().start()

    @receiver(pre_save, sender=CosinnusGroupMembership)
    def handle_membership_changed(sender, instance, **kwargs):
        """Updates an old RocketChat group membership when group or user are changed."""
        if instance.id:
            old_instance = CosinnusGroupMembership.objects.get(pk=instance.id)
            user_changed = instance.user_id != old_instance.user_id
            group_changed = instance.group_id != old_instance.group_id
            # Invalidate old membership
            if user_changed or group_changed:
                rocket_group_membership_update_task.delay(old_instance.user.pk, old_instance.group.pk)

    @receiver(post_save, sender=CosinnusGroupMembership)
    def handle_membership_updated(sender, instance, created, **kwargs):
        """Update RocketChat group membership."""
        if instance.user.is_guest:
            return
        rocket_group_membership_update_task.delay(instance.user.pk, instance.group.pk)

    @receiver(post_delete, sender=CosinnusGroupMembership)
    def handle_membership_deleted(sender, instance, **kwargs):
        """Delete RocketChat group membership."""
        if instance.user.is_guest:
            return
        rocket_group_membership_update_task.delay(instance.user.pk, instance.group.pk)

    @receiver(post_save, sender=Event)
    @receiver(post_save, sender=Note)
    def handle_relay_message_updated(sender, instance, created, **kwargs):
        if hasattr(instance, 'is_hidden_group_proxy') and instance.is_hidden_group_proxy:
            # Don't relay conference proxy events.
            return
        if created:
            # Not a threaded call as event and note settings are updated
            try:
                rocket = RocketChatConnection()
                rocket.relay_message_create(instance)
            except RocketChatDownException:
                logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
            except Exception as e:
                logger.exception(e)
        else:
            # prefetch related objects and do a threaded call
            prefetch_related_objects([instance], 'group__portal')

            class CosinnusRocketRelayMessageUpdateThread(Thread):
                def run(self):
                    try:
                        rocket = RocketChatConnection()
                        rocket.relay_message_update(instance)
                    except RocketChatDownException:
                        logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                    except Exception as e:
                        logger.exception(e)

            CosinnusRocketRelayMessageUpdateThread().start()

    @receiver(post_delete, sender=Event)
    @receiver(post_delete, sender=Note)
    def handle_relay_message_deleted(sender, instance, **kwargs):
        if hasattr(instance, 'is_hidden_group_proxy') and instance.is_hidden_group_proxy:
            # Conference proxy events are not relayed.
            return

        # do a threaded call
        class CosinnusRocketRelayMessageDeleteThread(Thread):
            def run(self):
                try:
                    rocket = RocketChatConnection()
                    rocket.relay_message_delete(instance)
                except RocketChatDownException:
                    logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                except Exception as e:
                    logger.exception(e)

        CosinnusRocketRelayMessageDeleteThread().start()

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
            # do a threaded call
            class CosinnusRocketConferenceRoomDeleteThread(Thread):
                def run(self):
                    try:
                        rocket = RocketChatConnection()
                        rocket.delete_private_room(instance.rocket_chat_room_id)
                    except RocketChatDownException:
                        logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                    except Exception as e:
                        logger.exception(e)

            CosinnusRocketConferenceRoomDeleteThread().start()
