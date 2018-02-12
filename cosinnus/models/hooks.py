# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.models.group import CosinnusGroup, CosinnusPortalMembership, \
    MEMBERSHIP_MEMBER, CosinnusGroupMembership, CosinnusPortal
from cosinnus.utils.user import assign_user_to_default_auth_group, \
    ensure_user_to_default_portal_groups
from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver

from cosinnus.models.tagged import ensure_container
from cosinnus.core.registries.group_models import group_model_registry

import logging
from django.contrib.auth.signals import user_logged_in
from cosinnus.models.profile import GlobalBlacklistedEmail,\
    GlobalUserNotificationSetting
from cosinnus.models.feedback import CosinnusFailedLoginRateLimitLog
from django.db import transaction

from cosinnus.core.middleware.login_ratelimit_middleware import login_ratelimit_triggered
from django.utils.encoding import force_text

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
            CosinnusPortalMembership.objects.get_or_create(user=membership.user, group=membership.group.portal, defaults={'status': MEMBERSHIP_MEMBER})
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
        CosinnusPortalMembership.objects.get_or_create(user=user, group=CosinnusPortal.get_current(), defaults={'status': MEMBERSHIP_MEMBER})
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
    except Exception, e:
        logger.error('Error while trying to log failed login ratelimit trigger!', extra={'exception': force_text(e)})

login_ratelimit_triggered.connect(on_login_ratelimit_triggered)
    
    
from cosinnus.apis.cleverreach import *
