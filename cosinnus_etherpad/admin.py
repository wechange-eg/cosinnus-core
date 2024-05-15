# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from cosinnus.admin import BaseHierarchicalTaggableAdmin
from cosinnus_etherpad.models import Etherpad


class EtherpadAdmin(BaseHierarchicalTaggableAdmin):
    # disabled, because dangerous
    # actions = ['reinit_pads',]

    list_display = BaseHierarchicalTaggableAdmin.list_display + [
        'type',
    ]
    list_filter = BaseHierarchicalTaggableAdmin.list_filter + ['type']

    def reinit_pads(self, request, queryset):
        """Converts this CosinnusGroup's type"""
        reinited_names = []
        for pad in queryset:
            if not pad.is_container:
                pad.reinit_pad()
                reinited_names.append(pad.title)

        message = _('The following Pads were re-initialized:') + '\n' + ', '.join(reinited_names)
        self.message_user(request, message)

    reinit_pads.short_description = _("Reinit Pads (do not use if you don't know what this is!)")


admin.site.register(Etherpad, EtherpadAdmin)
