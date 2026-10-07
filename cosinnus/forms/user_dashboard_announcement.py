# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from django import forms
from extra_views import InlineFormSetFactory

from cosinnus.conf import settings
from cosinnus.forms.group import AsssignPortalMixin
from cosinnus.forms.widgets import SplitHiddenDateWidget
from cosinnus.models.user_dashboard_announcement import (
    UserDashboardAnnouncement,
    UserDashboardAnnouncementCallToActionButton,
    UserDashboardWelcomeAnnouncement,
    UserDashboardWelcomeAnnouncementCallToActionButton,
)


class UserDashboardAnnouncementCallToActionButtonForm(forms.ModelForm):
    class Meta:
        model = UserDashboardAnnouncementCallToActionButton
        fields = (
            'dashboard_announcement',
            'label',
            'url',
        )


class UserDashboardAnnouncementCallToActionButtonInlineFormset(InlineFormSetFactory):
    factory_kwargs = {
        'extra': 10,
        'max_num': 10,
    }
    form_class = UserDashboardAnnouncementCallToActionButtonForm
    model = UserDashboardAnnouncementCallToActionButton


class UserDashboardAnnouncementForm(AsssignPortalMixin, forms.ModelForm):
    class Meta(object):
        model = UserDashboardAnnouncement
        if settings.COSINNUS_USE_V3_PERSONAL_DASHBOARD:
            fields = [
                'is_active',
                'valid_from',
                'valid_till',
                'title',
                'category',
                'text',
                'image',
                'display',
                'text_col_1',
                'text_col_2',
                'call_to_action_active',
            ]
        else:
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
        if not settings.COSINNUS_USE_V3_PERSONAL_DASHBOARD:
            self.fields['text'].initial = (
                '# Enter your\n# Big Headline here\n\nDear Community,\n\nExample text.\n\n## Secondary Headline\n\n'
                'More text'
            )
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


class UserDashboardWelcomeAnnouncementForm(AsssignPortalMixin, forms.ModelForm):
    """Welcome announcement for the v3 personal dashboard."""

    class Meta:
        model = UserDashboardWelcomeAnnouncement
        fields = [
            'is_active',
            'display_duration',
            'title',
            'display',
            'image',
            'text',
            'text_col_1',
            'text_col_2',
            'call_to_action_active',
        ]


class UserDashboardWelcomeAnnouncementCallToActionButtonForm(forms.ModelForm):
    class Meta:
        model = UserDashboardWelcomeAnnouncementCallToActionButton
        fields = (
            'welcome_announcement',
            'label',
            'url',
        )


class UserDashboardWelcomeAnnouncementCallToActionButtonInlineFormset(InlineFormSetFactory):
    factory_kwargs = {
        'extra': 10,
        'max_num': 10,
    }
    form_class = UserDashboardWelcomeAnnouncementCallToActionButtonForm
    model = UserDashboardWelcomeAnnouncementCallToActionButton
