# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.core.management.base import BaseCommand

from cosinnus_cloud.utils.nextcloud import create_social_login_apps

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = 'Creates a wechange oauth provider app and a nextcloud social login client app.'

    def handle(self, *args, **options):
        success = create_social_login_apps()
        if success:
            print('Portal oauth provider app and nextcloud client app created/synced successfully.')
