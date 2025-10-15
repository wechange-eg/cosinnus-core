# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.core.management.base import BaseCommand

from cosinnus.conf import settings
from cosinnus.core.middleware.cosinnus_middleware import (
    initialize_cosinnus_after_startup,
)
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_cloud.hooks import generate_group_nextcloud_id, get_nc_user_id
from cosinnus_cloud.utils import nextcloud
from cosinnus_cloud.utils.cosinnus import is_deck_enabled_for_group
from cosinnus_cloud.utils.nextcloud import OCSException
from cosinnus_deck.deck import DeckConnection

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = (
        'Checks all active groups without a deck id to create any missing nextcloud decks.'
        'Missing nextcloud groups are also created.'
    )

    def handle(self, *args, **options):
        try:
            initialize_cosinnus_after_startup()
            self.stdout.write('Checking active groups and creating any missing nextcloud decks.')
            counter = 0
            groups_created = 0
            users_added = 0
            decks_created = 0
            errors = 0

            groups = get_cosinnus_group_model().objects.all_in_portal()
            groups_without_deck = groups.filter(nextcloud_deck_board_id=None)
            total_groups = len(groups_without_deck)
            for group in groups_without_deck:
                counter += 1
                # only run this for groups that have the cloud app activated
                if is_deck_enabled_for_group(group):
                    # create and validate group
                    if not group.nextcloud_group_id:
                        generate_group_nextcloud_id(group, save=False)
                        group.save()

                    # create group
                    nextcloud_group_exists = True
                    try:
                        response = nextcloud.create_group(group.nextcloud_group_id)
                        if response:
                            groups_created += 1
                    except OCSException as e:
                        if not e.statuscode == 102:  # 102: group already exists
                            nextcloud_group_exists = False
                            errors += 1
                            self.stdout.write(f"Error (group create): OCSException: '{e.message}' ({e.statuscode})")
                    except Exception as e:
                        if settings.DEBUG:
                            raise
                        nextcloud_group_exists = False
                        errors += 1
                        self.stdout.write('Error (group create): Exception: ' + str(e))
                        logger.error('Error (nextcloud group create): Exception: ' + str(e), extra={'exc': e})

                    # proceed with next group if the nextcloud group could not be created
                    if not nextcloud_group_exists:
                        continue

                    # add members to group
                    nextcloud_user_ids = [get_nc_user_id(member) for member in group.actual_members]
                    # always add admin to groups
                    nextcloud_user_ids.append(settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME)
                    for nc_uid in nextcloud_user_ids:
                        try:
                            nextcloud.add_user_to_group(nc_uid, group.nextcloud_group_id)
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
                            self.stdout.write('Error (add user to group): Exception: ' + str(e))
                            logger.error('Error (nextcloud group user add): Exception: ' + str(e), extra={'exc': e})

                    # create deck
                    try:
                        deck = DeckConnection()
                        deck.group_board_create(group)
                        decks_created += 1
                    except Exception as e:
                        if settings.DEBUG:
                            raise
                        errors += 1
                        self.stdout.write('Error (create deck): Exception: ' + str(e))
                        logger.error('Error (nextcloud deck create): Exception: ' + str(e), extra={'exc': e})

                self.stdout.write(
                    f'{counter}/{total_groups} groups processed, {groups_created} groups created, {decks_created} '
                    f'group decks created, {users_added} groups members added ({errors} Errors)',
                )

            self.stdout.write(
                f'Done! {counter}/{total_groups} groups processed, {groups_created} groups created, {decks_created} '
                f'group decks created, {users_added} groups members added ({errors} Errors)',
            )

        except Exception:
            if settings.DEBUG:
                raise
