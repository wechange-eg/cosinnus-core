# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models.fields import BLANK_CHOICE_DASH
from django import forms

from cosinnus.models.newsletter import Newsletter


class UserWelcomeEmailForm(forms.Form):
    is_active = forms.BooleanField(required=False)
    email_text = forms.CharField(required=False, strip=False, widget=forms.Textarea)


class NewsletterForGroupForm(forms.ModelForm):

    class Meta(object):
        model = Newsletter
        fields = ['subject', 'body']

    def __init__(self, *args, **kwargs):
        self.groups = kwargs.pop('groups')
        if 'group' in kwargs:
            self.selected_group = kwargs.pop('group')
        super().__init__(*args, **kwargs)
        if hasattr(self, 'selected_group') and self.selected_group:
            self.fields['group'] = forms.ChoiceField(
                choices=BLANK_CHOICE_DASH + self.groups, initial=self.selected_group)
        else:
            self.fields['group'] = forms.ChoiceField(choices=BLANK_CHOICE_DASH + self.groups)

    def save(self, commit=True):
        newsletter = super().save()
        group_id = self.cleaned_data.get('group')
        newsletter.recipients_source = 'group@{}'.format(str(group_id))
        newsletter.save()
        return newsletter