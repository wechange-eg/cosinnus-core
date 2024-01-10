# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django import forms
from django.utils.translation import gettext_lazy as _

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
        self.fields['raw_html'].initial = """
Paste your raw HTML here. Use one of these button codes as "Do not show this again"-Button:

<a class="pale-color pale-with-highlight"
    data-target="ui-pref" data-ui-pref="dashboard_announcements__hidden"
    data-ui-pref-value="%(announcement_id)s" data-hide-after=".dashboard-announcement-frame">
    <i class="fas fa-close"></i>
</a>

or 

<h2>
<a class="pale-color pale-bold pale-with-highlight"
    data-target="ui-pref" data-ui-pref="dashboard_announcements__hidden"
    data-ui-pref-value="%(announcement_id)s" data-hide-after=".dashboard-announcement-frame">
    Hinweis nicht wieder anzeigen</a>
</h2>
        """
        
