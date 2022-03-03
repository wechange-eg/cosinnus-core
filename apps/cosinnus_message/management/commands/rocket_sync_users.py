import logging

from django.core.management.base import BaseCommand

from cosinnus_message.rocket_chat import RocketChatConnection
from cosinnus.conf import settings


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """
    Sync users with Rocket.Chat
    """
    
    def add_arguments(self, parser):
        parser.add_argument('-s', '--skip-update', action='store_true', help='Skip updating existing users')


    def handle(self, *args, **options):
        skip_update = options['skip_update']
        
        if not settings.COSINNUS_CHAT_USER:
            return
        rocket = RocketChatConnection(stdout=self.stdout, stderr=self.stderr)
        rocket.users_sync(skip_update=skip_update)
