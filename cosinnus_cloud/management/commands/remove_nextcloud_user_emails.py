# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import traceback

from django.core.management.base import BaseCommand
from django.utils.encoding import force_str

from cosinnus.conf import settings
from cosinnus.core.middleware.cosinnus_middleware import (
    initialize_cosinnus_after_startup,
)
from django.contrib.auth import get_user_model
from cosinnus_cloud.hooks import create_user_from_obj, get_nc_user_id,\
    update_user_from_obj
from cosinnus_cloud.utils.nextcloud import OCSException, list_all_users
from cosinnus.utils.user import filter_active_users, filter_portal_users
from cosinnus_cloud.utils import nextcloud


logger = logging.getLogger("cosinnus")


class Command(BaseCommand):
    help = "Updates all users' email addresses. Was used once to set all emails to empty. "

    def handle(self, *args, **options):
        try:
            initialize_cosinnus_after_startup()
            self.stdout.write(
                "Updating all users email adresses."
            )
            counter = 0
            updated = 0
            errors = 0
            # retrieve all existing users so we don't update ones without email
            existing_nc_users = list_all_users()
            total_users = len(existing_nc_users)
            self.stdout.write(
                f"Updating {total_users} users."
            )
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
                    self.stdout.write(
                        f"Error: OCSException: '{e.message}' ({e.statuscode})"
                    )
                        
                except Exception as e:
                    if settings.DEBUG:
                        raise
                    errors += 1
                    self.stdout.write("Error: Exception: " + str(e))
                self.stdout.write(
                    f"{counter}/{total_users} users checked, {updated} nextcloud users updated ({errors} Errors)",
                    ending="\r",
                )
                self.stdout.flush()
            self.stdout.write(
                f"Done! {counter}/{total_users} users checked, {updated} nextcloud users updated ({errors} Errors)."
            )
        except Exception as e:
            if settings.DEBUG:
                raise
