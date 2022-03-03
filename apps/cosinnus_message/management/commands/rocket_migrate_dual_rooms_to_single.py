import logging

from django.core.management.base import BaseCommand

from cosinnus.conf import settings
from cosinnus.models.profile import PROFILE_SETTING_ROCKET_CHAT_ID
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_message.rocket_chat import RocketChatConnection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """
    Sync users with Rocket.Chat
    """
    
    def add_arguments(self, parser):
        parser.add_argument('-s', '--skip-rename', action='store_true', help='Skip renaming existing rooms (if the room name schema didn\'t change)')


    def handle(self, *args, **options):
        skip_rename = options['skip_rename']
        
        if not settings.COSINNUS_CHAT_USER:
            return
        # sanity checks
        if len(settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS) > 1:
            self.stdout.write('*Aborting*: there seems to be more than one rocketchat channel configured in `COSINNUS_ROCKET_GROUP_ROOM_KEYS`. This migration can only be run to go from a dual-room ("general" and "news" as it was) to a single-room configuration.')
            return
        if len(settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS) == 0:
            self.stdout.write('*Aborting*: there seems to be no rocketchat configured in `COSINNUS_ROCKET_GROUP_ROOM_KEYS`. This would archive *all* the rocketchat channels!')
            return
        
        rocket = RocketChatConnection(stdout=self.stdout, stderr=self.stderr)
        portal_groups = get_cosinnus_group_model().objects.all_in_portal()
        count = 0
        errors = 0
        total = len(portal_groups)
        for group in portal_groups:
            # go through the group settings and find any saved room connections
            deleted_keys = []
            renamed = False
            error = False
            for setting_key, setting_value in group.settings.items():
                if setting_key.startswith(f'{PROFILE_SETTING_ROCKET_CHAT_ID}_'):
                    room_key = setting_key.replace(f'{PROFILE_SETTING_ROCKET_CHAT_ID}_', '', 1)
                    # if the room key no longer exists in the settings, *archive* the room and remove the key from the settings
                    if not room_key in settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS:
                        # go by direct room ids, because the room key is not configured any more
                        if not rocket.groups_archive(group, specific_room_ids=[setting_value]):
                            error = True
                            self.stdout.write(f'\tError during group {group.slug} room archive: {room_key}: {setting_value} ')
                            break
                        deleted_keys.append(setting_key)
                        
            if not error:
                # soft-save the group if the settings object was changed
                if deleted_keys:
                    for deleted_key in deleted_keys:
                        del group.settings[deleted_key]
                    type(group).objects.filter(pk=group.pk).update(settings=group.settings)
                
                # call a rename on the group, so that the changed channel naming pattern is applied
                if not skip_rename:
                    if not rocket.groups_rename(group):
                        self.stdout.write(f'\tError during group rename: {group.slug}')
                        error = True
                    renamed = True
                
            if error:
                errors += 1
            
            count += 1
            self.stdout.write(f'Processed group {count}/{total} ({errors} Errors) ("{group.slug}"): {"**Error!**" if error else ""} Delete channels: {deleted_keys}. Trigger rename: {renamed} ')
            
            
            
        