# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django import forms
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.forms.group import AsssignPortalMixin
from cosinnus.models.user_dashboard_announcement import UserDashboardAnnouncement


class UserDashboardAnnouncementForm(AsssignPortalMixin, forms.ModelForm):
    
    class Meta(object):
        model = UserDashboardAnnouncement
        fields = [
            'is_active', 
            'valid_from',
            'valid_till',
            'title',
            'category',
            'type',
            'text',
            'raw_html',
            'image', 
            'url',
        ]


