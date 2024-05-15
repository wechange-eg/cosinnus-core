import logging

from django.core.management.base import BaseCommand

from cosinnus.conf import settings
from cosinnus_message.rocket_chat import RocketChatConnection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """
    Sync groups with Rocket.Chat
    """

    def handle(self, *args, **options):
        if not settings.COSINNUS_CHAT_USER:
            return

        rocket = RocketChatConnection(stdout=self.stdout, stderr=self.stderr)
        rocket.groups_sync()
