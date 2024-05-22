# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

import django
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_mailbox.models import Mailbox

from cosinnus.models.group import CosinnusPortal

# we need this import here!
from cosinnus_message.conf import settings  # noqa


class CosinnusMailbox(Mailbox):
    objects = models.Manager()

    portal = models.ForeignKey(
        CosinnusPortal,
        verbose_name=_('Portal'),
        related_name='mailboxes',
        null=False,
        blank=False,
        default=1,
        on_delete=models.CASCADE,
    )  # port_id 1 is created in a datamigration!

    class Meta(object):
        verbose_name = 'Cosinnus Mailbox'
        verbose_name_plural = 'Cosinnus Mailboxes'


if django.VERSION[:2] < (1, 7):
    from cosinnus_message import cosinnus_app

    cosinnus_app.register()
