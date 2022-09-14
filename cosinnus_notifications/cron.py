# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.utils.timezone import now
from django_cron import Schedule

from cosinnus.cron import CosinnusCronJobBase
from cosinnus_notifications.models import NotificationAlert
from django.contrib.auth import get_user_model
from datetime import timedelta


logger = logging.getLogger('cosinnus')

OLD_NOTIFICATION_THRESHOLD_DAYS = 365


class DeleteOldNotificationAlerts(CosinnusCronJobBase):
    """ Delete all NotificationAlerts older than a set date. """
    
    RUN_EVERY_MINS = 60*24*7 # every 7 days
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    
    cosinnus_code = 'cosinnus.delete_old_notification_alerts'
    
    def do(self):
        delete_old_notification_alerts(do_per_user=False, do_print=False)
        

def delete_old_notification_alerts(do_per_user=False, do_print=False):
    threshold = now() - timedelta(days=OLD_NOTIFICATION_THRESHOLD_DAYS)
    queryset = NotificationAlert.objects.filter(last_event_at__lte=threshold)
    if do_per_user:
        for user in get_user_model().objects.all():
            result = queryset.filter(user=user).delete()
            if do_print:
                print(f'>>> deleting notifications for user {user.id}')
                print(result)
    else:
        result = queryset.delete()
        if do_print:
            print(result)
        
