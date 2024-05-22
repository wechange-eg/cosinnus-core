import logging

from django.core.management.base import BaseCommand

from cosinnus.conf import settings
from cosinnus_message.rocket_chat import RocketChatConnection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """
    Sync settings with Rocket.Chat
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--only-settings',
            help='Sync only listed settings (format: Setting_1,Setting_2,Setting_3).',
        )

    def handle(self, *args, **options):
        if not settings.COSINNUS_CHAT_USER:
            return

        only_settings = options['only_settings'].split(',') if options['only_settings'] else None
        rocket = RocketChatConnection(stdout=self.stdout, stderr=self.stderr)
        rocket.settings_update(only_settings=only_settings)
