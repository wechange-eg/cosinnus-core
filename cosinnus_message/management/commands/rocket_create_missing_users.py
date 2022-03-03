import logging

from django.core.management.base import BaseCommand

from cosinnus_message.rocket_chat import RocketChatConnection
from cosinnus.conf import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """
    Create missing user accounts in rocketchat (and verify that ones with an existing
    connection still exist in rocketchat properly).
    Inactive user accounts and ones that never logged in will also be created.
    Will never create accounts for users with __unverified__ emails.
        
    @param --skip-inactive: if given, will not create any accounts for inactive users
    @param --force-group-membership-sync: if given, will also re-do and sync all group
        memberships, for all users. (default: only sync memberships for users created 
        during this run)
    
    """
    
    def add_arguments(self, parser):
        parser.add_argument('-s', '--skip-inactive', action='store_true', help='Skip updating inactive users')
        parser.add_argument('-f', '--force-group-membership-sync', action='store_true', help='Sync ALL users\' group memberships')

    def handle(self, *args, **options):
        if not settings.COSINNUS_CHAT_USER:
            return
        
        skip_inactive = options['skip_inactive']
        force_group_membership_sync = options['force_group_membership_sync']
        
        rocket = RocketChatConnection(stdout=self.stdout, stderr=self.stderr)
        rocket.create_missing_users(skip_inactive=skip_inactive, force_group_membership_sync=force_group_membership_sync)
