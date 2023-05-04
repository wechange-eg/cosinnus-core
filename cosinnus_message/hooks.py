from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from oauth2_provider.signals import app_authorized

from cosinnus_message.rocket_chat import RocketChatConnection,\
    delete_cached_rocket_connection
from cosinnus.models import UserProfile, CosinnusGroupMembership, MEMBERSHIP_PENDING, MEMBERSHIP_INVITED_PENDING, \
    MEMBERSHIP_ADMIN
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
            try:
                old_instance = get_user_model().objects.get(pk=instance.id)
                force = any([getattr(instance, fname) != getattr(old_instance, fname) \
                                for fname in ('password', 'first_name', 'last_name', 'email')])
                password_updated = bool(instance.password != old_instance.password)
                # do a threaded call
                class CosinnusRocketUpdateThread(Thread):
                    def run(self):
                        rocket = RocketChatConnection()
                        rocket.users_update(instance, force_user_update=force, update_password=password_updated)
                CosinnusRocketUpdateThread().start()
            except Exception as e:
                logger.exception(e)
    
    @receiver(user_logged_in)
    def handle_user_logged_in(sender, user, request, **kwargs):
        """ Checks if the user exists in rocketchat, and if not, attempts to create them """
        # we're Threading this entire hook as it might take a while
        class UserSanityCheck(Thread):
            def run(self):
                try:
                    rocket = RocketChatConnection()
                    rocket.ensure_user_account_sanity(user)
                except Exception as e:
                    logger.exception(e)
        
        UserSanityCheck().start()
    
    @receiver(signals.user_password_changed)
    def handle_user_password_updated(sender, user, **kwargs):
        try:
            # do a threaded call
            class CosinnusRocketPasswordUpdateThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    rocket.users_update(user, force_user_update=True, update_password=True)
                    delete_cached_rocket_connection(user.cosinnus_profile.rocket_username)
            CosinnusRocketPasswordUpdateThread().start()
        except Exception as e:
            logger.exception(e)

    @receiver(post_save, sender=UserProfile)
    def handle_profile_updated(sender, instance, created, **kwargs):
        # only update active profiles (inactive ones should be disabled in rocketchat also)
        if not instance.user.is_active:
            return

        try:
            if created:
                # User creation is blocking to avoid concurrency problem with subsequente profile update calls.
                rocket = RocketChatConnection()
                rocket.users_create(instance.user)
            else:
                # do a threaded call
                class CosinnusRocketProfileUpdateThread(Thread):
                    def run(self):
                        rocket = RocketChatConnection()
                        rocket.users_update(instance.user)
                CosinnusRocketProfileUpdateThread().start()
        except Exception as e:
            logger.exception(e)

    @receiver(pre_save, sender=CosinnusSociety)
    @receiver(pre_save, sender=CosinnusProject)
    @receiver(pre_save, sender=CosinnusConference)
    def handle_cosinnus_group_updated(sender, instance, **kwargs):
        try:
            old_instance = get_object_or_None(type(instance), pk=instance.id) if instance.id else None

            # do a threaded call
            class CosinnusRocketGroupUpdateThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    if old_instance and rocket.get_group_id(instance, create_if_not_exists=False):
                        if instance.slug != old_instance.slug:
                            rocket.groups_rename(instance)
                    else:
                        rocket.groups_create(instance)
            CosinnusRocketGroupUpdateThread().start()
        except Exception as e:
            logger.exception(e)

    @receiver(post_delete, sender=CosinnusSociety)
    @receiver(post_delete, sender=CosinnusProject)
    @receiver(post_delete, sender=CosinnusConference)
    def handle_cosinnus_group_deleted(sender, instance, **kwargs):
        try:
            # do a threaded call
            class CosinnusRocketGroupDeleteThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    rocket.groups_delete(instance)
            CosinnusRocketGroupDeleteThread().start()
        except Exception as e:
            logger.exception(e)
            
    @receiver(signals.group_deactivated)
    def handle_cosinnus_group_deactivated(sender, group, **kwargs):
        """ Archive a group that gets deactivated """
        try:
            # do a threaded call
            class CosinnusRocketGroupDeactivateThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    rocket.groups_archive(group)
            CosinnusRocketGroupDeactivateThread().start()
        except Exception as e:
            logger.exception(e)
    
    @receiver(signals.group_reactivated)
    def handle_cosinnus_group_reactivated(sender, group, **kwargs):
        """ Unarchive a group that gets reactivated """
        try:
            # do a threaded call
            class CosinnusRocketGroupReactivateThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    rocket.groups_unarchive(group)
            CosinnusRocketGroupReactivateThread().start()
        except Exception as e:
            logger.exception(e)

    @receiver(signals.user_deactivated)
    def user_deactivated(sender, user, **kwargs):
        """ Deactivate a rocketchat user account """
        try:
            # do a threaded call
            class CosinnusRocketUserDeactivateThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    rocket.users_disable(user)
            CosinnusRocketUserDeactivateThread().start()
        except Exception as e:
            logger.exception(e)
    
    @receiver(signals.user_activated)
    def user_activated(sender, user, **kwargs):
        """ Activate a rocketchat user account """
        try:
            # do a threaded call
            class CosinnusRocketUserActivateThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    rocket.users_enable(user)
            CosinnusRocketUserActivateThread().start()
        except Exception as e:
            logger.exception(e)
        
    @receiver(pre_save, sender=CosinnusGroupMembership)
    def handle_membership_updated(sender, instance, **kwargs):
        try:
            is_pending = instance.status in (MEMBERSHIP_PENDING, MEMBERSHIP_INVITED_PENDING)
            if instance.id:
                old_instance = CosinnusGroupMembership.objects.get(pk=instance.id)  # Could be None
                was_pending = old_instance.status in (MEMBERSHIP_PENDING, MEMBERSHIP_INVITED_PENDING)
                user_changed = instance.user_id != old_instance.user_id
                group_changed = instance.group_id != old_instance.group_id
                is_moderator_changed = instance.status != old_instance.status and \
                                       (instance.status == MEMBERSHIP_ADMIN or old_instance.status == MEMBERSHIP_ADMIN)

                # do a threaded call
                class CosinnusRocketMembershipUpdateThread(Thread):
                    def run(self):
                        rocket = RocketChatConnection()
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
                CosinnusRocketMembershipUpdateThread().start()
            elif not is_pending:
                # do a threaded call
                class CosinnusRocketMembershipCreateThread(Thread):
                    def run(self):
                        rocket = RocketChatConnection()
                        # Create new membership
                        rocket.groups_invite(instance)
                        if instance.status == MEMBERSHIP_ADMIN:
                            rocket.groups_add_moderator(instance)
                CosinnusRocketMembershipCreateThread().start()
        except Exception as e:
            logger.exception(e)

    @receiver(post_delete, sender=CosinnusGroupMembership)
    def handle_membership_deleted(sender, instance, **kwargs):
        try:
            # do a threaded call
            class CosinnusRocketMembershipDeletedThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    rocket.groups_kick(instance)
            CosinnusRocketMembershipDeletedThread().start()
        except Exception as e:
            logger.exception(e)

    @receiver(post_save, sender=Event)
    @receiver(post_save, sender=Note)
    def handle_relay_message_updated(sender, instance, created, **kwargs):
        try:
            # do a threaded call
            class CosinnusRocketRelayMessageUpdateThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    if created:
                        rocket.relay_message_create(instance)
                    else:
                        rocket.relay_message_update(instance)
            CosinnusRocketRelayMessageUpdateThread().start()
        except Exception as e:
            logger.exception(e)

    @receiver(post_delete, sender=Event)
    @receiver(post_delete, sender=Note)
    def handle_relay_message_deleted(sender, instance, **kwargs):
        try:
            # do a threaded call
            class CosinnusRocketRelayMessageDeleteThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    rocket.relay_message_delete(instance)
            CosinnusRocketRelayMessageDeleteThread().start()
        except Exception as e:
            logger.exception(e)

    @receiver(signals.pre_userprofile_delete)
    def handle_user_deleted(sender, profile, **kwargs):
        """ Called when a user deletes their account. Completely deletes the user's rocket profile """
        try:
            # do a threaded call
            class CosinnusRocketUserDeleteThread(Thread):
                def run(self):
                    rocket = RocketChatConnection()
                    rocket.users_delete(profile.user)
            CosinnusRocketUserDeleteThread().start()
        except Exception as e:
            logger.exception(e)
