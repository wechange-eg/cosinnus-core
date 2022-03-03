# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from cosinnus_message.conf import settings # we need this import here!

from django_mailbox.models import Mailbox
from cosinnus.models.group import CosinnusPortal
from django.db import models
from django.utils.translation import ugettext_lazy as _


class CosinnusMailbox(Mailbox):
    
    objects = models.Manager()
    
    portal = models.ForeignKey(CosinnusPortal, verbose_name=_('Portal'), related_name='mailboxes', 
        null=False, blank=False, default=1, on_delete=models.CASCADE) # port_id 1 is created in a datamigration!
    
    class Meta(object):
        verbose_name = "Cosinnus Mailbox"
        verbose_name_plural = "Cosinnus Mailboxes"


import django
if django.VERSION[:2] < (1, 7):
    from cosinnus_message import cosinnus_app
    cosinnus_app.register()


