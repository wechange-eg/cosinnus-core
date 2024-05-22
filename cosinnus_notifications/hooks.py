# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from annoying.functions import get_object_or_None
from django.dispatch.dispatcher import receiver

from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus_notifications.models import UserNotificationPreference
from cosinnus_notifications.notifications import ALL_NOTIFICATIONS_ID


@receiver(signals.user_joined_group)
def assign_default_group_notification_preference_on_group_join(sender, user, group, **kwargs):
    """Assign each user the default group notification preference when he joins a group"""
    default_setting = settings.COSINNUS_DEFAULT_GROUP_NOTIFICATION_SETTING
    # set the notifications_all setting to the default setting or create it
    pref_all = get_object_or_None(
        UserNotificationPreference, user=user, group=group, notification_id=ALL_NOTIFICATIONS_ID
    )
    if not pref_all:
        pref_all = UserNotificationPreference.objects.create(
            user=user, group=group, notification_id=ALL_NOTIFICATIONS_ID, setting=default_setting
        )
