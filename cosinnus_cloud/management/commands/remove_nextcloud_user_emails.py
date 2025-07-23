# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.core.management.base import BaseCommand

from cosinnus.conf import settings
from cosinnus.core.middleware.cosinnus_middleware import (
    initialize_cosinnus_after_startup,
)
from cosinnus_cloud.utils import nextcloud
from cosinnus_cloud.utils.nextcloud import OCSException, list_all_users

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = "Set all nextcloud users' email addresses to empty. "

    def handle(self, *args, **options):
        try:
            initialize_cosinnus_after_startup()
            self.stdout.write('Updating all users email adresses.')
            counter = 0
            updated = 0
            errors = 0
            # retrieve all existing users so we don't update ones without email
            existing_nc_users = list_all_users()
            total_users = len(existing_nc_users)
            self.stdout.write(f'Updating {total_users} users.')
            for user_id in existing_nc_users:
                counter += 1
                try:
                    nextcloud.update_user_email(
                        user_id,
                        '',
                    )
                    updated += 1
                except OCSException as e:
                    errors += 1
                    self.stdout.write(f"Error: OCSException: '{e.message}' ({e.statuscode})")

                except Exception as e:
                    if settings.DEBUG:
                        raise
                    errors += 1
                    self.stdout.write('Error: Exception: ' + str(e))
                self.stdout.write(
                    f'{counter}/{total_users} users checked, {updated} nextcloud users updated ({errors} Errors)',
                    ending='\r',
                )
                self.stdout.flush()
            self.stdout.write(
                f'Done! {counter}/{total_users} users checked, {updated} nextcloud users updated ({errors} Errors).'
            )
        except Exception:
            if settings.DEBUG:
                raise
