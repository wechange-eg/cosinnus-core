# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.core.management.base import BaseCommand

from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
from cosinnus_notifications.cron import delete_old_notification_alerts

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = 'Deletes old notification alerts, per user'

    def handle(self, *args, **options):
        initialize_cosinnus_after_startup()
        delete_old_notification_alerts(do_per_user=True, do_print=True)
