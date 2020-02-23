# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django import forms
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.forms.group import AsssignPortalMixin
from cosinnus.models.user_dashboard_announcement import UserDashboardAnnouncement
from cosinnus.forms.widgets import SplitHiddenDateWidget


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
        
    valid_from = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='00:00'))
    valid_till = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='23:59'))
    
    def __init__(self, *args, **kwargs):
        super(UserDashboardAnnouncementForm, self).__init__(*args, **kwargs)
        self.fields['text'].initial = "# Enter your\n# Big Headline here\n\nDear Community,\n\nExample text.\n\n## Secondary Headline\n\nMore text"

