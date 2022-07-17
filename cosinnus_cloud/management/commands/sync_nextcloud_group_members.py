# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import traceback

from django.core.management.base import BaseCommand
from django.utils.encoding import force_text

from cosinnus.conf import settings
from cosinnus.core.middleware.cosinnus_middleware import (
    initialize_cosinnus_after_startup,
)
from django.contrib.auth import get_user_model
from cosinnus_cloud.hooks import get_nc_user_id
from cosinnus_cloud.utils.nextcloud import OCSException
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_cloud.utils import nextcloud
from cosinnus.models.group import CosinnusPortal
from cosinnus.utils.user import is_user_active
from cosinnus_cloud.utils.cosinnus import is_cloud_enabled_for_group


logger = logging.getLogger("cosinnus")


class Command(BaseCommand):
    help = "Checks all active groups to create any missing nextcloud group membership associations for users"

    def handle(self, *args, **options):
        if not settings.COSINNUS_CLOUD_ENABLED:
            self.stdout.write('COSINNUS_CLOUD_ENABLED is not True, aborting.')
            return 
        
        try:
            initialize_cosinnus_after_startup()
            portal = CosinnusPortal.get_current()
            self.stdout.write(
                f"Checking active users and creates any missing group memberships for portal {portal.slug}."
            )
            counter = 0
            errors = 0
            users_added = 0

            portal_groups = get_cosinnus_group_model().objects.all_in_portal()
            total_groups = len(portal_groups)
            for group in portal_groups:
                counter += 1
                # only run this for groups that have the cloud app activated
                if is_cloud_enabled_for_group(group):
                    # add members to group
                    nextcloud_user_ids = [get_nc_user_id(member) for member in group.actual_members if is_user_active(member)]
                    # except for empty groups
                    if len(nextcloud_user_ids) == 0:
                        continue
                    # always add admin to groups
                    nextcloud_user_ids.append(settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME) 
                    for nc_uid in nextcloud_user_ids:
                        try:
                            nextcloud.add_user_to_group(
                                nc_uid, group.nextcloud_group_id
                            )
                            users_added += 1
                        except OCSException as e:
                            errors += 1
                            self.stdout.write(
                                f"Error (add user to group): OCSException: '{e.message}' ({e.statuscode})"
                            )
                        except Exception as e:
                            if settings.DEBUG:
                                raise
                            errors += 1
                            self.stdout.write(
                                "Error (add user to group): Exception: " + str(e)
                            )
                            logger.error("Error (nextcloud group user add): Exception: " + str(e), extra={"exc": e})
                self.stdout.write(
                    f"{counter}/{total_groups} groups processed, {users_added} groups members added ({errors} Errors)",
                )
                
            self.stdout.write(
                f"Done! {counter}/{total_groups} groups processed, {users_added} groups members added ({errors} Errors)."
            )
        except Exception as e:
            if settings.DEBUG:
                raise
