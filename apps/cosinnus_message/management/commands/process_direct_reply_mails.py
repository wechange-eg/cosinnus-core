import logging

from django.core.management.base import BaseCommand

from cosinnus_message.utils.utils import process_direct_reply_messages,\
    update_mailboxes


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """ Downloads all mail for mailboxes in this portal, then processes direct replies as answers. """
    
    def handle(self, *args, **options):
        update_mailboxes()
        process_direct_reply_messages()
        