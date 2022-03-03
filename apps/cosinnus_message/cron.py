# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django_cron import CronJobBase, Schedule

from cosinnus.cron import CosinnusCronJobBase
from cosinnus_message.utils.utils import update_mailboxes,\
    process_direct_reply_messages
from django.utils.encoding import force_text

logger = logging.getLogger('cosinnus')

class ProcessDirectReplyMails(CosinnusCronJobBase):
    """ Downloads all mail for mailboxes in this portal, then processes direct replies as answers. """
    
    RUN_EVERY_MINS = 1 # every 1 minute
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    
    cosinnus_code = 'message.process_direct_reply_mails'
    
    def do(self):
        update_mailboxes()
        try:
            process_direct_reply_messages()
        except Exception as e:
            logger.error('Process_direct_reply_messages() threw an exception! (in extra)', extra={'exception': force_text(e)})
            