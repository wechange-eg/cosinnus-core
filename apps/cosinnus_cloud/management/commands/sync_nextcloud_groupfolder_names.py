# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.core.management.base import BaseCommand
from cosinnus_cloud.utils.nextcloud import get_groupfolder_name
from cosinnus.conf import settings
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_cloud.utils.cosinnus import is_cloud_enabled_for_group



logger = logging.getLogger("cosinnus")


class Command(BaseCommand):
    help = "Syncs the plattform's `groups.nextcloud_groupfolder_name` field entries with the actual current remote folder names in nextcloud. Helpful to repair broken folder associations after the cloud folder rename bugfix. Won't change anything in the nextcloud."

    def handle(self, *args, **options):
        if not getattr(settings, "COSINNUS_CLOUD_ENABLED", False):
            self.stdout.write('Cloud is not enabled')
            return
        
        counter = 0
        checked = 0
        renamed = 0
        errors = 0
        
        portal_groups = get_cosinnus_group_model().objects.all_in_portal()
        total_groups = len(portal_groups)
        for group in portal_groups:
            counter += 1
            # only run this for groups that have the cloud app activated
            if is_cloud_enabled_for_group(group) and \
                    group.nextcloud_group_id and group.nextcloud_groupfolder_name and group.nextcloud_groupfolder_id:
                checked +=1
                
                remote_name_differed = False
                try:
                    remote_groupfolder_name = get_groupfolder_name(group.nextcloud_groupfolder_id)
                    if remote_groupfolder_name:
                        remote_name_differed = remote_groupfolder_name != group.nextcloud_groupfolder_name
                except Exception as e:
                    logger.warning('Nextcloud get_groupfolder_name failed!', extra={'group_id':group.id, 'groupfolder_id':group.nextcloud_groupfolder_id, 'exc': str(e)})
                    errors += 1
                if remote_name_differed and remote_groupfolder_name:
                    try:
                        self.stdout.write(f"\tSaving actual name '{remote_groupfolder_name}' instead of '{group.nextcloud_groupfolder_name}' for group {group.slug}.")
                        type(group).objects.filter(pk=group.pk).update(nextcloud_groupfolder_name=remote_groupfolder_name)
                        renamed += 1
                    except Exception as e:
                        logger.warning('Nextcloud group folder name fix failed!', extra={'group_id':group.id, 'groupfolder_id':group.nextcloud_groupfolder_id, 'exc': str(e)})
                        errors += 1
                
            self.stdout.write(
                f"{counter}/{total_groups} groups processed, {checked} cloud-enabled groups checked, {renamed} groupfolder names fixed ({errors} Errors)",
            )
    