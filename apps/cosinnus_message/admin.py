# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from cosinnus_message.models import CosinnusMailbox
from django_mailbox.admin import get_new_mail
from django_mailbox.models import Mailbox

class CosinnusMailboxAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'portal',
        'uri',
        'from_email',
        'active',
    )
    actions = [get_new_mail]

admin.site.register(CosinnusMailbox, CosinnusMailboxAdmin)
admin.site.unregister(Mailbox)
