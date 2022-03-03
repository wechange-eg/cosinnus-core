from __future__ import print_function
from builtins import object
import logging

from django.core.management.base import BaseCommand

from cosinnus_message.utils.utils import process_direct_reply_messages,\
    update_mailboxes


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """ Downloads all mail for mailboxes in this portal, then processes direct replies as answers. """
    
    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('hash', nargs='+', type=str)
        parser.add_argument('email', nargs='+', type=str)

    
    def handle(self, *args, **options):
        class FakeMessage(object):
            def __init__(self, hash, email, *args, **kwargs):
                self.text = 'woweee reply from direct fake\n> DIRECT-REPLY CODE: \n> directreply+1+%s+wachstumswende.de ' % hash[0]
                self.from_header = email[0]
                super(FakeMessage, self).__init__(*args, **kwargs)
                
        msg = FakeMessage(options['hash'], options['email'])
        print(">>> now processing a fake message")
        process_direct_reply_messages(messages=[msg], no_delete=True)
        print(">> done processing a fake message!")
        