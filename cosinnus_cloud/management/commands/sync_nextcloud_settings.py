# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.core.management.base import BaseCommand
from cosinnus_cloud.utils.nextcloud import apply_nextcloud_settings



logger = logging.getLogger("cosinnus")


class Command(BaseCommand):
    help = "Applies configured settings from conf `COSINNUS_CLOUD_NEXTCLOUD_SETTINGS` via OCS "

    def handle(self, *args, **options):
        apply_nextcloud_settings(print_to_console=True)
        print('Finished applying Nextcloud settings.')
        
    