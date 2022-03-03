import logging

from django.core.management.base import BaseCommand

from cosinnus_message.rocket_chat import RocketChatConnection
from cosinnus.conf import settings
from cosinnus.utils.user import filter_active_users, filter_portal_users
from django.contrib.auth import get_user_model


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """
    Sync users with Rocket.Chat
    """
    
    def handle(self, *args, **options):
        
        if not settings.COSINNUS_CHAT_USER:
            return
        rocket = RocketChatConnection(stdout=self.stdout, stderr=self.stderr)
        
        # Get existing rocket users
        rocket_users = {}
        rocket_emails_usernames = {}
        size = 100
        offset = 0
        while True:
            response = rocket.rocket.users_list(size=size, offset=offset).json()
            if not response.get('success'):
                self.stderr.write('users_sync: ' + str(response), response)
                break
            if response['count'] == 0:
                break

            for rocket_user in response['users']:
                rocket_users[rocket_user['username']] = rocket_user
                for email in rocket_user.get('emails', []):
                    if not email.get('address'):
                        continue
                    rocket_emails_usernames[email['address']] = rocket_user['username']
            offset += response['count']
            
        # Check active users in DB
        users = filter_active_users(filter_portal_users(get_user_model().objects.all()))
        count = len(users)
        for i, user in enumerate(users):
            self.stdout.write('User %i/%i \t(id: %i)' % (i, count, user.id))
            if not hasattr(user, 'cosinnus_profile'):
                self.stdout.write('\tSkipped!')
                return
            
            profile = user.cosinnus_profile
            rocket_username = profile.rocket_username

            rocket_user = rocket_users.get(rocket_username)
            
            # Username exists?
            if rocket_user:
                rocket.users_update(user, force_user_update=True)
            else:
                self.stdout.write('\ŧSkipped!')
