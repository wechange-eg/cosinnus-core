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
                rocket = RocketChatConnection()
                old_instance = get_user_model().objects.get(pk=instance.id)
                force = any([getattr(instance, fname) != getattr(old_instance, fname) \
                                for fname in ('password', 'first_name', 'last_name', 'email')])
                password_updated = bool(instance.password != old_instance.password)
                # do a threaded call
                class CosinnusRocketUpdateThread(Thread):
                    def run(self):
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
            rocket = RocketChatConnection()
            rocket.users_update(user, force_user_update=True, update_password=True)
            delete_cached_rocket_connection(user.cosinnus_profile.rocket_username)
        except Exception as e:
            logger.exception(e)

    @receiver(post_save, sender=UserProfile)
    def handle_profile_updated(sender, instance, created, **kwargs):
        # only update active profiles (inactive ones should be disabled in rocketchat also)
        if not instance.user.is_active:
            return
        
        try:
            if created:
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
    def handle_cosinnus_society_updated(sender, instance, **kwargs):
        try:
            rocket = RocketChatConnection()
            if instance.id:
                old_instance = get_object_or_None(CosinnusSociety, pk=instance.id)
                if old_instance and instance.slug != old_instance.slug:
                    rocket.groups_rename(instance)
            else:
                rocket.groups_create(instance)
        except Exception as e:
            logger.exception(e)

    @receiver(pre_save, sender=CosinnusProject)
    def handle_cosinnus_project_updated(sender, instance, **kwargs):
        try:
            rocket = RocketChatConnection()
            if instance.id:
                old_instance = get_object_or_None(CosinnusProject, pk=instance.id)
                if old_instance and instance.slug != old_instance.slug:
                    rocket.groups_rename(instance)
            else:
                rocket.groups_create(instance)
        except Exception as e:
            logger.exception(e)
            
    @receiver(pre_save, sender=CosinnusConference)
    def handle_cosinnus_conference_updated(sender, instance, **kwargs):
        try:
            rocket = RocketChatConnection()
            if instance.id:
                old_instance = get_object_or_None(CosinnusConference, pk=instance.id)
                if old_instance and instance.slug != old_instance.slug:
                    rocket.groups_rename(instance)
            else:
                rocket.groups_create(instance)
        except Exception as e:
            logger.exception(e)

    @receiver(post_delete, sender=CosinnusSociety)
    def handle_cosinnus_society_deleted(sender, instance, **kwargs):
        try:
            rocket = RocketChatConnection()
            rocket.groups_delete(instance)
        except Exception as e:
            logger.exception(e)
            
    @receiver(post_delete, sender=CosinnusProject)
    def handle_cosinnus_project_deleted(sender, instance, **kwargs):
        try:
            rocket = RocketChatConnection()
            rocket.groups_delete(instance)
        except Exception as e:
            logger.exception(e)
            
    @receiver(post_delete, sender=CosinnusConference)
    def handle_cosinnus_conference_deleted(sender, instance, **kwargs):
        try:
            rocket = RocketChatConnection()
            rocket.groups_delete(instance)
        except Exception as e:
            logger.exception(e)

    @receiver(signals.group_deactivated)
    def handle_cosinnus_group_deactivated(sender, group, **kwargs):
        """ Archive a group that gets deactivated """
        try:
            rocket = RocketChatConnection()
            rocket.groups_archive(group)
        except Exception as e:
            logger.exception(e)
    
    @receiver(signals.group_reactivated)
    def handle_cosinnus_group_reactivated(sender, group, **kwargs):
        """ Unarchive a group that gets reactivated """
        try:
            rocket = RocketChatConnection()
            rocket.groups_unarchive(group)
        except Exception as e:
            logger.exception(e)
            

    @receiver(signals.user_deactivated)
    def user_deactivated(sender, user, **kwargs):
        """ Deactivate a rocketchat user account """
        try:
            rocket = RocketChatConnection()
            rocket.users_disable(user)
        except Exception as e:
            logger.exception(e)
    
    @receiver(signals.user_activated)
    def user_activated(sender, user, **kwargs):
        """ Activate a rocketchat user account """
        try:
            rocket = RocketChatConnection()
            rocket.users_enable(user)
        except Exception as e:
            logger.exception(e)
        
    @receiver(pre_save, sender=CosinnusGroupMembership)
    def handle_membership_updated(sender, instance, **kwargs):
        try:
            rocket = RocketChatConnection()
            is_pending = instance.status in (MEMBERSHIP_PENDING, MEMBERSHIP_INVITED_PENDING)
            # do a threaded call
            class CosinnusRocketMembershipUpdateThread(Thread):
                def run(self):
                    if instance.id:
                        old_instance = CosinnusGroupMembership.objects.get(pk=instance.id)
                        was_pending = old_instance.status in (MEMBERSHIP_PENDING, MEMBERSHIP_INVITED_PENDING)
                        user_changed = instance.user_id != old_instance.user_id
                        group_changed = instance.group_id != old_instance.group_id
                        is_moderator_changed = instance.status != old_instance.status and \
                                (instance.status == MEMBERSHIP_ADMIN or old_instance.status == MEMBERSHIP_ADMIN)
            
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
                    elif not is_pending:
                        # Create new membership
                        rocket.groups_invite(instance)
                        if instance.status == MEMBERSHIP_ADMIN:
                            rocket.groups_add_moderator(instance)
            CosinnusRocketMembershipUpdateThread().start()
            
        except Exception as e:
            logger.exception(e)

    @receiver(post_delete, sender=CosinnusGroupMembership)
    def handle_membership_deleted(sender, instance, **kwargs):
        try:
            rocket = RocketChatConnection()
            # do a threaded call
            class CosinnusRocketMembershipDeletedThread(Thread):
                def run(self):
                    rocket.groups_kick(instance)
            CosinnusRocketMembershipDeletedThread().start()
        except Exception as e:
            logger.exception(e)

    @receiver(post_save, sender=Note)
    def handle_note_updated(sender, instance, created, **kwargs):
        try:
            rocket = RocketChatConnection()
            if created:
                rocket.notes_create(instance)
            else:
                rocket.notes_update(instance)
        except Exception as e:
            logger.exception(e)

    @receiver(post_delete, sender=Note)
    def handle_note_deleted(sender, instance, **kwargs):
        rocket = RocketChatConnection()
        rocket.notes_delete(instance)

    @receiver(signals.pre_userprofile_delete)
    def handle_user_deleted(sender, profile, **kwargs):
        """ Called when a user deletes their account. Completely deletes the user's rocket profile """
        rocket = RocketChatConnection()
        rocket.users_delete(profile.user)
