# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django_cron import Schedule

from cosinnus.cron import CosinnusCronJobBase
from cosinnus_notifications.models import NotificationAlert

logger = logging.getLogger('cosinnus')


OLD_NOTIFICATION_THRESHOLD_DAYS = 180


class DeleteOldNotificationAlerts(CosinnusCronJobBase):
    """Delete all NotificationAlerts older than a set date
    (number of days defined in `OLD_NOTIFICATION_THRESHOLD_DAYS`)."""

    RUN_EVERY_MINS = 60 * 24 * 7  # every 7 days
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.delete_old_notification_alerts'

    def do(self):
        count = delete_old_notification_alerts(do_per_user=False)
        return f'Deleted {count} notifications older than {OLD_NOTIFICATION_THRESHOLD_DAYS} days.'


def delete_old_notification_alerts(do_per_user=False):
    threshold = now() - timedelta(days=OLD_NOTIFICATION_THRESHOLD_DAYS)
    queryset = NotificationAlert.objects.filter(last_event_at__lte=threshold)
    count = queryset.count()
    if do_per_user:
        for user in get_user_model().objects.all():
            queryset.filter(user=user).delete()
    else:
        queryset.delete()
    return count
