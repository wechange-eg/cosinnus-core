# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import timedelta

from django.core.cache import cache
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus_notifications.models import NotificationAlert

logger = logging.getLogger('cosinnus')


ALERTS_USER_DATA_CACHE_KEY = 'cosinnus/core/alerts/user/%(user_id)s/data'

ALERT_REASONS = {
    'is_group': None,  # -- reason will not be shown. the item is a group and is always shown for invitations etc
    'is_creator': _('You are seeing this alert because you created this content.'),
    'follow_group': _("You are seeing this alert because you are following the item's project or group."),
    'follow_object': _('You are seeing this alert because you are following this item.'),
    'none': None,  # -- reason will not be shown
}


def create_user_alert(obj, group, receiver, action_user, notification_id, reason_key=None):
    """Creates a NotificationAlert for a NotificationEvent to someone who wants it.
    @param group: can be None (for non-group items or groups themselves)
    @param reason_key: a key of `ALERT_REASONS` or None."""

    # create preliminary alert (not persisted yet!)
    alert = NotificationAlert()
    alert.initialize(
        user=receiver, target_object=obj, group=group, action_user=action_user, notification_id=notification_id
    )
    # generate some derived data in the alert derived from its object/event
    alert.fill_notification_dependent_data()
    alert.reason_key = reason_key

    # Case A: check if the alert should be merged into an existing multi user alert
    # multi user check: the owner is same, and the item_hash matches,
    # and the existing alert is a single alert or already a multi alert
    if alert.get_allowed_type() == NotificationAlert.TYPE_MULTI_USER_ALERT:
        multi_user_qs = NotificationAlert.objects.filter(
            portal=CosinnusPortal.get_current(),
            user=alert.user,
            item_hash=alert.item_hash,
            type__in=[NotificationAlert.TYPE_SINGLE_ALERT, NotificationAlert.TYPE_MULTI_USER_ALERT],
        )
        multi_user_qs = list(multi_user_qs)
        if len(multi_user_qs) > 1:
            logger.warning(
                'Inconsistency: Trying to match a multi user alert, but had a QS with more than 1 items!',
                extra={'alert': str(alert)},
            )
            if settings.DEBUG:
                raise Exception('DEBUG ERROR: Multi alert double inconsistency')
        elif len(multi_user_qs) == 1:
            multi_alert = multi_user_qs[0]
            merge_new_alert_into_multi_alert(alert, multi_alert)
            return

    # Case B: if no matching alerts for multi alerts were found, check if a bundle alert matches:
    # bundle alert check: the owner is same, datetime < 3h, the bundle_hash matches
    # and the existing alert is a single alert or already a bundle alert
    # TODO: optionize the timeframe
    if alert.get_allowed_type() == NotificationAlert.TYPE_BUNDLE_ALERT:
        a_short_time_ago = now() - timedelta(hours=3)
        bundle_qs = NotificationAlert.objects.filter(
            portal=CosinnusPortal.get_current(),
            user=alert.user,
            last_event_at__gte=a_short_time_ago,
            bundle_hash=alert.bundle_hash,
            type__in=[NotificationAlert.TYPE_SINGLE_ALERT, NotificationAlert.TYPE_BUNDLE_ALERT],
        )
        bundle_qs = list(bundle_qs)
        if len(bundle_qs) > 1:
            logger.warning(
                'Inconsistency: Trying to match a multi user alert, but had a QS with more than 1 items!',
                extra={'alert': str(alert)},
            )
            if settings.DEBUG:
                raise Exception('DEBUG ERROR: Bundle alert double inconsistency')
        elif len(bundle_qs) == 1:
            merge_new_alert_into_bundle_alert(alert, bundle_qs[0])
            return

    # Case C: if the event caused neither a multi user alert or bundle alert, save alert as a new alert
    alert.generate_label()
    alert.save()

    # delete user-entry cache to be fresh instantly alerts on refresh
    cache_key = ALERTS_USER_DATA_CACHE_KEY % {'user_id': receiver.id}
    cache.delete(cache_key)


def merge_new_alert_into_multi_alert(new_alert, multi_alert):
    """Merges a newly arrived alert into an existing alert as multi alert.
    The existing alert may yet still be a single alert"""
    # sanity check, cannot convert bundle alerts
    if multi_alert.type not in (NotificationAlert.TYPE_SINGLE_ALERT, NotificationAlert.TYPE_MULTI_USER_ALERT):
        logger.warning(
            'Inconsistency: Trying to create a multi user alert, but matched existing alert was a bundle alert!',
            extra={'alert': str(multi_alert)},
        )
        return

    is_repeat_alert = bool(
        new_alert.action_user == multi_alert.action_user
        or any([user_item['user_id'] == new_alert.action_user.id for user_item in multi_alert.multi_user_list])
    )

    # if there was a matching alert with the user not in the multi_user_list, merge the alerts.
    # make the old alert a multi alert, add the new action user and reset it to be current
    if not is_repeat_alert and multi_alert.type == NotificationAlert.TYPE_SINGLE_ALERT:
        multi_alert.type = NotificationAlert.TYPE_MULTI_USER_ALERT
        # save aways the old (first) action user first
        multi_alert.add_new_multi_action_user(multi_alert.action_user)
        multi_alert.counter = 1

    # re-fill the cached data (so the most recent user and object is always the target)
    multi_alert.last_event_at = now()
    multi_alert.seen = False
    multi_alert.action_user = new_alert.action_user
    multi_alert.target_object = new_alert.target_object
    multi_alert.fill_notification_dependent_data()
    multi_alert.generate_label()

    # If the new alert's action_user is any of the action_users in the old alert, we only bump this alert to most recent
    #     and make it unseen. this is case like a user editing or liking/unliking an item multiple times,
    #     but we're not gonna try to be a "smart" here, and hide the alert from the user at risk of omitting important events
    # Else, for non-repeated alerts (alert from a new user), we bump the counter and add the user to the list
    if not is_repeat_alert:
        multi_alert.counter += 1
        multi_alert.add_new_multi_action_user(new_alert.action_user)

    multi_alert.save()


def merge_new_alert_into_bundle_alert(new_alert, bundle_alert):
    """Merges a newly arrived alert into an existing alert as bundle alert.
    The existing alert may yet still be a single alert"""
    # sanity check, cannot convert multi alerts
    if bundle_alert.type not in (NotificationAlert.TYPE_SINGLE_ALERT, NotificationAlert.TYPE_BUNDLE_ALERT):
        logger.warning(
            'Inconsistency: Trying to create a bundle alert, but matched existing alert was a multi user alert!',
            extra={'alert': str(bundle_alert)},
        )
        return

    # If the new alert's target_object is any of the bundle objects in the old alert, we only bump this alert to most recent
    # and make it unseen. this is case like users editing items multiple times in a short time frame
    # but we're not gonna try to be a "smart" here, and hide the alert from the user at risk of omitting important events
    if new_alert.target_object == bundle_alert.target_object or any(
        [bundle_item['object_id'] == new_alert.object_id for bundle_item in bundle_alert.bundle_list]
    ):
        bundle_alert.last_event_at = now()
        bundle_alert.seen = False
        bundle_alert.target_object = new_alert.target_object
        bundle_alert.target_title = new_alert.target_title
        bundle_alert.target_url = new_alert.target_url
        bundle_alert.icon_or_image_url = new_alert.icon_or_image_url
        bundle_alert.save()
        return

    # make the old alert a bundle alert, add the new alert to the bundle and reset it to be current
    if bundle_alert.type == NotificationAlert.TYPE_SINGLE_ALERT:
        bundle_alert.type = NotificationAlert.TYPE_BUNDLE_ALERT
        bundle_alert.add_new_bundle_item(bundle_alert)
        bundle_alert.counter = 1
    bundle_alert.last_event_at = now()
    bundle_alert.seen = False
    bundle_alert.counter += 1
    bundle_alert.target_object = new_alert.target_object
    bundle_alert.add_new_bundle_item(new_alert)
    bundle_alert.generate_label()
    bundle_alert.save()
