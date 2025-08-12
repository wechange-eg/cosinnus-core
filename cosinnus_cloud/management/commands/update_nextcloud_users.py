# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from cosinnus.conf import settings
from cosinnus.core.middleware.cosinnus_middleware import (
    initialize_cosinnus_after_startup,
)
from cosinnus.utils.user import filter_active_users, filter_portal_users
from cosinnus_cloud.hooks import get_nc_user_id, update_user_from_obj, update_user_profile_avatar
from cosinnus_cloud.utils.nextcloud import OCSException, list_all_users

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = "Updates all active users' names and email addresses in their nextcloud profile. Will not create new users."

    def handle(self, *args, **options):
        try:
            initialize_cosinnus_after_startup()
            self.stdout.write('Updating all existing users email profiles.')
            counter = 0
            updated = 0
            skipped = 0
            errors = 0

            all_users = filter_active_users(filter_portal_users(get_user_model().objects.all()))
            # retrieve all existing users so we don't try to update nonexisting ones
            existing_nc_users = list_all_users()

            total = all_users.count()
            self.stdout.write(f'Updating {total} users.')
            for user in all_users:
                counter += 1

                # only update user if it is already in NC user DB with their id
                if get_nc_user_id(user) not in existing_nc_users:
                    skipped += 1
                    continue

                try:
                    update_user_from_obj(user)
                    if hasattr(user, 'cosinnus_profile'):
                        update_user_profile_avatar(user.cosinnus_profile, retry=False)
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
                    f'{counter}/{total} done, {updated} updated, {skipped} non-existing skipped ({errors} Errors)',
                    ending='\r',
                )
                self.stdout.flush()
            self.stdout.write(
                f'Done! {counter}/{total} done, {updated} updated, {skipped} non-existing skipped ({errors} Errors).'
            )
        except Exception:
            if settings.DEBUG:
                raise
