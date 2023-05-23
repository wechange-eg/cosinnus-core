from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import prefetch_related_objects
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from oauth2_provider.signals import app_authorized

from cosinnus_message.rocket_chat import RocketChatConnection, RocketChatDownException, \
    delete_cached_rocket_connection
from cosinnus.models import UserProfile, CosinnusGroupMembership, MEMBERSHIP_PENDING, MEMBERSHIP_INVITED_PENDING, \
    MEMBERSHIP_ADMIN
from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject,\
    CosinnusConference
from cosinnus_event.models import Event
from cosinnus_note.models import Note
from cosinnus.core import signals

import logging
from django.contrib.auth.signals import user_logged_in
from threading import Thread
from annoying.functions import get_object_or_None
logger = logging.getLogger(__name__)


if settings.COSINNUS_ROCKET_ENABLED:
    def handle_app_authorized(sender, request, token, **kwargs):
        rocket = RocketChatConnection()
        rocket.users_create_or_update(token.user, request=request)

    app_authorized.connect(handle_app_authorized)
    
    @receiver(pre_save, sender=get_user_model())
    def handle_user_updated(sender, instance, **kwargs):
        # TODO: does this hook trigger correctly?
        # this handles the user update, it is not in post_save!
        if instance.id and hasattr(instance, 'cosinnus_profile'):
            old_instance = get_user_model().objects.get(pk=instance.id)
            force = any([getattr(instance, fname) != getattr(old_instance, fname) \
                            for fname in ('password', 'first_name', 'last_name', 'email')])
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
        """ Checks if the user exists in rocketchat, and if not, attempts to create them """
        # we're Threading this entire hook as it might take a while
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
            if old_instance and rocket.get_group_id(instance, create_if_not_exists=False):
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
        """ Archive a group that gets deactivated """
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
        """ Unarchive a group that gets reactivated """
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
        """ Deactivate a rocketchat user account """
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
        """ Activate a rocketchat user account """
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
    def handle_membership_updated(sender, instance, **kwargs):
        is_pending = instance.status in (MEMBERSHIP_PENDING, MEMBERSHIP_INVITED_PENDING)
        if instance.id:
            old_instance = CosinnusGroupMembership.objects.get(pk=instance.id)
            was_pending = old_instance.status in (MEMBERSHIP_PENDING, MEMBERSHIP_INVITED_PENDING)
            user_changed = instance.user_id != old_instance.user_id
            group_changed = instance.group_id != old_instance.group_id
            is_moderator_changed = instance.status != old_instance.status and \
                                   (instance.status == MEMBERSHIP_ADMIN or old_instance.status == MEMBERSHIP_ADMIN)

            # prefetch related objects and do a threaded call
            prefetch_related_objects([instance], 'group')
            prefetch_related_objects([instance], 'user__cosinnus_profile')
            class CosinnusRocketMembershipUpdateThread(Thread):
                def run(self):
                    try:
                        rocket = RocketChatConnection()
                        # Check if a default channel exists for a conference. If not there is nothing to be done.
                        if _group_is_conference_without_default_channel(rocket, instance.group):
                            return

                        # Invalidate old membership
                        if (is_pending and not was_pending) or user_changed or group_changed:
                            rocket.groups_kick(old_instance)

                        # Create new membership
                        if (was_pending and not is_pending) or user_changed or group_changed:
                            rocket.groups_invite(instance)

                        # Update membership
                        if not is_pending and is_moderator_changed:
                            # Upgrade
                            if not old_instance.status == MEMBERSHIP_ADMIN and instance.status == MEMBERSHIP_ADMIN:
                                rocket.groups_add_moderator(instance)
                            # Downgrade
                            elif old_instance.status == MEMBERSHIP_ADMIN and not instance.status == MEMBERSHIP_ADMIN:
                                rocket.groups_remove_moderator(instance)
                    except RocketChatDownException:
                        logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                    except Exception as e:
                        logger.exception(e)
            CosinnusRocketMembershipUpdateThread().start()
        elif not is_pending:
            # prefetch related objects and do a threaded call
            prefetch_related_objects([instance], 'group')
            prefetch_related_objects([instance], 'user__cosinnus_profile')
            class CosinnusRocketMembershipCreateThread(Thread):
                def run(self):
                    try:
                        rocket = RocketChatConnection()
                        # Check if a default channel exists for a conference. If not there is nothing to be done.
                        if _group_is_conference_without_default_channel(rocket, instance.group):
                            return
                        # Create new membership
                        rocket.groups_invite(instance)
                        if instance.status == MEMBERSHIP_ADMIN:
                            rocket.groups_add_moderator(instance)
                    except RocketChatDownException:
                        logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                    except Exception as e:
                        logger.exception(e)
            CosinnusRocketMembershipCreateThread().start()

    @receiver(post_delete, sender=CosinnusGroupMembership)
    def handle_membership_deleted(sender, instance, **kwargs):
        try:
            # prefetch related objects and do a threaded call
            prefetch_related_objects([instance], 'group')
            prefetch_related_objects([instance], 'user__cosinnus_profile')
            class CosinnusRocketMembershipDeletedThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    # Check if a default channel exists for a conference. If not there is nothing to be done.
                    if _group_is_conference_without_default_channel(rocket, instance.group):
                        return
                    rocket.groups_kick(instance)
            CosinnusRocketMembershipDeletedThread().start()
        except RocketChatDownException:
            logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
        except Exception as e:
            logger.exception(e)

    @receiver(post_save, sender=Event)
    @receiver(post_save, sender=Note)
    def handle_relay_message_updated(sender, instance, created, **kwargs):
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
        """ Called when a user deletes their account. Completely deletes the user's rocket profile """
        # Not a threaded call as run with management command
        try:
            rocket = RocketChatConnection()
            rocket.users_delete(profile.user)
        except RocketChatDownException:
            logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
        except Exception as e:
            logger.exception(e)

    @receiver(post_delete, sender=CosinnusConferenceRoom)
    def handle_conference_room_deleted(sender, instance, **kwargs):
        """ Called when a conference room is deleted. Delete the corresponding group. """
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
