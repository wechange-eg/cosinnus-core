# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from annoying.functions import get_object_or_None
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.signals import post_delete, pre_save
from django.db.models.signals import post_save
from django.dispatch import receiver

from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.core.middleware.login_ratelimit_middleware import login_ratelimit_triggered
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.models.feedback import CosinnusFailedLoginRateLimitLog
from cosinnus.models.group import CosinnusGroup, CosinnusPortalMembership, \
    CosinnusGroupMembership
from cosinnus.models.membership import MEMBERSHIP_MEMBER, MEMBER_STATUS, \
    MEMBERSHIP_ADMIN
from cosinnus.models.profile import GlobalBlacklistedEmail, \
    GlobalUserNotificationSetting, get_user_profile_model
from cosinnus.models.tagged import ensure_container, LikeObject
from cosinnus.models.widget import WidgetConfig
from cosinnus.utils.dashboard import ensure_group_widget
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.user import assign_user_to_default_auth_group, \
    ensure_user_to_default_portal_groups
from cosinnus.models.managed_tags import CosinnusManagedTagAssignment,\
    CosinnusManagedTag
from cosinnus.models.group_extra import ensure_group_type

logger = logging.getLogger('cosinnus')

User = get_user_model()


@receiver(post_delete)
def clear_cache_on_group_delete(sender, instance, **kwargs):
    """ Clears the cache on CosinnusGroups after deleting one of them. """
    if sender == CosinnusGroup or issubclass(sender, CosinnusGroup):
        instance._clear_cache(slug=instance.slug)


def ensure_user_in_group_portal(sender, created, **kwargs):
    """ Whenever a group membership is created, make sure the user is in the Portal for this group """
    if created:
        try:
            membership = kwargs.get('instance')
            CosinnusPortalMembership.objects.get_or_create(user=membership.user, group=membership.group.portal,
                                                           defaults={'status': MEMBERSHIP_MEMBER})
        except:
            # We fail silently, because we never want to 500 here unexpectedly
            logger.error("Error while trying to add User Portal Membership for user that has just joined a group.")


# makes sure that users gain membership in a Portal when they are added into a group in that portal
post_save.connect(ensure_user_in_group_portal, sender=CosinnusGroupMembership)

post_save.connect(assign_user_to_default_auth_group, sender=User)
post_save.connect(ensure_user_to_default_portal_groups, sender=CosinnusPortalMembership)


@receiver(user_logged_in)
def ensure_user_in_logged_in_portal(sender, user, request, **kwargs):
    """ Make sure on user login, that the user becomes a member of this portal """
    try:
        CosinnusPortalMembership.objects.get_or_create(user=user, group=CosinnusPortal.get_current(),
                                                       defaults={'status': MEMBERSHIP_MEMBER})
    except:
        # We fail silently, because we never want to 500 here unexpectedly
        logger.error("Error while trying to add User Portal Membership for user that has just logged in.")


@receiver(user_logged_in)
def ensure_user_blacklist_converts_to_setting(sender, user, request, **kwargs):
    """ Make sure on user login, that the user becomes a member of this portal """
    try:
        email = user.email
        if GlobalBlacklistedEmail.is_email_blacklisted(email):
            with transaction.atomic():
                GlobalBlacklistedEmail.remove_for_email(email)
                settings_obj = GlobalUserNotificationSetting.objects.get_object_for_user(user)
                settings_obj.setting = GlobalUserNotificationSetting.SETTING_NEVER
                settings_obj.save()
    except:
        # We fail silently, because we never want to 500 here unexpectedly
        logger.error("Error while trying to add User Portal Membership for user that has just logged in.")
        if settings.DEBUG:
            raise


post_save.connect(ensure_container, sender=CosinnusGroup)
for url_key in group_model_registry:
    group_model = group_model_registry.get(url_key)
    post_save.connect(ensure_container, sender=group_model)


def on_login_ratelimit_triggered(sender, username, ip, **kwargs):
    """ Log rate limit attempts """
    try:
        CosinnusFailedLoginRateLimitLog.objects.create(username=username, ip=None, portal=CosinnusPortal.get_current())
    except Exception as e:
        logger.error('Error while trying to log failed login ratelimit trigger!', extra={'exception': force_text(e)})


login_ratelimit_triggered.connect(on_login_ratelimit_triggered)


@receiver(user_logged_in)
def set_cookie_expiry_for_authenticated_user(sender, user, request, **kwargs):
    """ Default for cookies for anonymous users is browser-session and as set in 
        `COSINNUS_SESSION_EXPIRY_AUTHENTICATED_IN_USERS` logged in users """
    request.session.set_expiry(settings.COSINNUS_SESSION_EXPIRY_AUTHENTICATED_IN_USERS)


@receiver(user_logged_out)
def reset_cookie_expiry_for_anonymous_user(sender, user, request, **kwargs):
    """ Default for cookies for anonymous users is browser-session and as set in 
        `COSINNUS_SESSION_EXPIRY_AUTHENTICATED_IN_USERS` logged in users """
    request.session.set_expiry(0)


if getattr(settings, 'COSINNUS_USER_FOLLOWS_GROUP_WHEN_JOINING', True):

    @receiver(signals.user_joined_group)
    def user_follow_joined_group_trigger(sender, user, group, **kwargs):
        """ Will automatically make a user follow a group after they joined it """
        group_ct = ContentType.objects.get_for_model(get_cosinnus_group_model())
        # create a new followed likeobject
        likeobj, created = LikeObject.objects.get_or_create(
            content_type=group_ct,
            object_id=group.id,
            user=user,
            defaults={'liked': False, 'followed': True}
        )
        # or make the existing likeobject followed
        if not created:
            if not likeobj.followed:
                likeobj.followed = True
                likeobj.save(update_fields=['followed'])
        group.clear_likes_cache()


    @receiver(signals.user_left_group)
    def user_unfollow_left_group_trigger(sender, user, group, **kwargs):
        """ Will automatically make a user unfollow a group after they left it """
        group_ct = ContentType.objects.get_for_model(get_cosinnus_group_model())
        # get an existing following object
        likeobj = get_object_or_None(LikeObject,
                                     content_type=group_ct,
                                     object_id=group.id,
                                     user=user,
                                     followed=True
                                     )
        # make the followed likeobject unfollowed if it exists
        if likeobj:
            likeobj.followed = False
            likeobj.save(update_fields=['followed'])
            group.clear_likes_cache()

""" User account activation/deactivation logic """


def user_pre_save(sender, **kwargs):
    """ Saves a user's is_active value as it was before saving """
    user = kwargs['instance']
    actual_value = user.is_active
    try:
        user.refresh_from_db(fields=['is_active'])
    except get_user_model().DoesNotExist:
        # happens on user create
        pass
    user._is_active = user.is_active
    user.is_active = actual_value


def user_post_save(sender, **kwargs):
    """ Compares the saved is_active value and sends signals if it was changed """
    user = kwargs['instance']
    if hasattr(user, '_is_active'):
        if user.is_active != user._is_active:
            if user.is_active:
                signals.user_activated.send(sender=sender, user=user)
            else:
                signals.user_deactivated.send(sender=sender, user=user)


pre_save.connect(user_pre_save, sender=get_user_model())
post_save.connect(user_post_save, sender=get_user_model())


@receiver(signals.group_apps_activated)
def group_cloud_app_activated_sub(sender, group, apps, **kwargs):
    """ Whenever a group app is activated, make sure all dashboard widgets have a config instance. """
    for app_name, widget_name, options in settings.COSINNUS_INITIAL_GROUP_WIDGETS:
        ensure_group_widget(group, app_name, widget_name, WidgetConfig.TYPE_DASHBOARD, options)


@receiver(signals.group_membership_has_changed)
def group_membership_has_changed_sub(sender, instance, deleted, **kwargs):
    """ Called after a CosinusGroupMembership is changed, to apply changes to BBBRoom models in conference """

    # we're Threading this entire hook as it might take a while
    class MembershipUpdateHookThread(Thread):
        def run(self):

            # everything is only real membership changes, not for non-invitations:
            if deleted or instance.status in MEMBER_STATUS:

                # assign users to the group's BBBRoom's members if one exists
                room = instance.group.media_tag.bbb_room
                if room:
                    if deleted:
                        room.remove_user(instance.user)
                    else:
                        if instance.status in MEMBER_STATUS:
                            room.join_user(instance.user, as_moderator=bool(instance.status==MEMBERSHIP_ADMIN))

                # For group conferences:
                group = instance.group
                user = instance.user
                if group.group_is_conference:

                    # if the group is a conference and there are any ResultProjects in any conference room,
                    # mirror the membership change to those result projects
                    result_groups = group.conference_group_result_projects
                    for result_group in result_groups:
                        # apply the same membership status to the result_group as it was in the conference group
                        membership = get_object_or_None(CosinnusGroupMembership, group=result_group, user=user)
                        if deleted:
                            if membership:
                                membership.delete()
                            continue
                        if membership and membership.status != instance.status:
                            membership.status = instance.status
                            membership.save()
                        if not membership:
                            CosinnusGroupMembership.objects.create(group=result_group, user=user, status=instance.status)

                    # if there are any rocketchat rooms, update the rocketchat group membership for those rooms
                    if settings.COSINNUS_ROCKET_ENABLED:
                        rocket_rooms = list(CosinnusConferenceRoom.objects.filter(group=group, type__in=CosinnusConferenceRoom.ROCKETCHAT_ROOM_TYPES))
                        if len(rocket_rooms) > 0:

                            from cosinnus_message.rocket_chat import RocketChatConnection
                            rocket = RocketChatConnection()
                            # add/remove member from each rocketchat room for each conference room
                            for room in rocket_rooms:
                                try:
                                    room.sync_rocketchat_room()
                                    if not room.rocket_chat_room_id:
                                        logger.error('Wanted to sync a user membership to a conference room, but a rocketchat room for it could not be created!',
                                                    extra={'room': room.id})
                                        continue
                                    if deleted:
                                        # kicked member
                                        rocket.remove_member_from_room(user, room.rocket_chat_room_id)
                                    else:
                                        rocket.add_member_to_room(user, room.rocket_chat_room_id)
                                        # Update membership
                                        if instance.status == MEMBERSHIP_ADMIN:
                                            # Upgrade
                                            rocket.add_moderator_to_room(user, room.rocket_chat_room_id)
                                        else:
                                            # Downgrade
                                            rocket.remove_moderator_from_room(user, room.rocket_chat_room_id)
                                except Exception as e:
                                    logger.exception(e)

    MembershipUpdateHookThread().start()


@receiver(post_save, sender=CosinnusManagedTagAssignment)
def managed_tag_sync_paired_group_memebership_creation(sender, instance, created, **kwargs):
    """ If a managed tag has a paired group and has been assigned (and approved) to a user profile,
        create the user's group membership in the paired group if it doesn't exist yet """
    try:
        target_object = instance.target_object
        if instance.approved and target_object and isinstance(target_object, get_user_profile_model()):
            tag = instance.managed_tag
            if tag.paired_group:
                membership = get_object_or_None(CosinnusGroupMembership, group=tag.paired_group, user=target_object.user)
                if membership and not membership.status in MEMBER_STATUS:
                    membership.status = MEMBERSHIP_MEMBER
                    membership.save()
                elif not membership:
                    CosinnusGroupMembership.objects.create(
                        group=tag.paired_group, 
                        user=target_object.user,
                        status=MEMBERSHIP_MEMBER
                    )
    except Exception as e:
        logger.exception(e)


@receiver(post_delete, sender=CosinnusManagedTagAssignment)
def managed_tag_sync_paired_group_memebership_deletion(sender, instance, **kwargs):
    """ If a managed tag has a paired group and has been unassigned from a user profile,
        delete the user's group membership in the paired group (unless the user is a group admin) """
    try:
        target_object = instance.target_object
        if target_object and type(target_object) is get_user_profile_model():
            tag = instance.managed_tag
            if tag.paired_group:
                membership = get_object_or_None(CosinnusGroupMembership, group=tag.paired_group, user=target_object.user)
                if membership and not membership.status == MEMBERSHIP_ADMIN:
                    membership.delete()
    except Exception as e:
        logger.exception(e)
        

@receiver(post_save, sender=CosinnusManagedTagAssignment)
@receiver(post_delete, sender=CosinnusManagedTagAssignment)
def managed_tag_assignment_update(sender, instance, created=False, **kwargs):
    """ Update the target object's index on managed tag assignment """
    try:
        target_object = instance.target_object
        if target_object and hasattr(target_object, 'update_index'):
            target_object.update_index()
    except Exception as e:
        logger.exception(e)
        

@receiver(post_save, sender=CosinnusManagedTag)
@receiver(post_delete, sender=CosinnusManagedTag)
def managed_tag_cache_clear_triggers(sender, instance, created=False, **kwargs):
    """ Clears the cache for tags when saved/deleted """
    try:
        CosinnusManagedTag.objects.clear_cache()
    except Exception as e:
        logger.exception(e)
        

@receiver(post_save, sender=CosinnusGroupMembership)
@receiver(post_delete, sender=CosinnusGroupMembership)
def group_membership_cache_clear_triggers(sender, instance, created=False, **kwargs):
    """ Clears the cache for CosinnusGroupMembership when saved/deleted """
    try:
        CosinnusGroupMembership.clear_member_cache_for_group(instance.group)
    except Exception as e:
        logger.exception(e)


from cosinnus.apis.cleverreach import * # noqa
from cosinnus.models.wagtail_models import *  # noqa
