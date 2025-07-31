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
from cosinnus_cloud.hooks import create_user_from_obj, get_nc_user_id, update_user_profile_avatar
from cosinnus_cloud.utils.nextcloud import OCSException, list_all_users

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = 'Checks all active users to create any missing nextcloud user accounts. Will not update existing users.'

    def handle(self, *args, **options):
        try:
            initialize_cosinnus_after_startup()
            self.stdout.write('Checking active users and creating any missing nextcloud user accounts.')
            counter = 0
            created = 0
            errors = 0
            all_users = filter_active_users(filter_portal_users(get_user_model().objects.all()))

            # retrieve all existing users so we don't create them anew
            existing_nc_users = list_all_users()
            total_users = len(all_users)
            for user in all_users:
                counter += 1

                # only add user if not already in NC user DB with their id
                if get_nc_user_id(user) not in existing_nc_users:
                    try:
                        create_user_from_obj(user)
                        if hasattr(user, 'cosinnus_profile') and user.cosinnus_profile.avatar:
                            update_user_profile_avatar(user.cosinnus_profile, retry=False)
                        created += 1
                    except OCSException as e:
                        if not e.statuscode == 102:  # 102: user already exists
                            errors += 1
                            self.stdout.write(f"Error: OCSException: '{e.message}' ({e.statuscode})")
                    except Exception as e:
                        if settings.DEBUG:
                            raise
                        errors += 1
                        self.stdout.write('Error: Exception: ' + str(e))
                self.stdout.write(
                    f'{counter}/{total_users} users checked, {created} nextcloud users created ({errors} Errors)',
                    ending='\r',
                )
                self.stdout.flush()
            self.stdout.write(
                f'Done! {counter}/{total_users} users checked, {created} nextcloud users created ({errors} Errors).'
            )
        except Exception:
            if settings.DEBUG:
                raise
