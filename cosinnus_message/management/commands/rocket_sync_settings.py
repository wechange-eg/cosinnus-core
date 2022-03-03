import logging

from django.core.management.base import BaseCommand

from cosinnus_message.rocket_chat import RocketChatConnection
from cosinnus.conf import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """
    Sync settings with Rocket.Chat
    """

    def handle(self, *args, **options):
        if not settings.COSINNUS_CHAT_USER:
            return
        
        rocket = RocketChatConnection(stdout=self.stdout, stderr=self.stderr)
        rocket.settings_update()
