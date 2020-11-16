# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models.fields import BLANK_CHOICE_DASH
from django import forms

from cosinnus.models.managed_tags import CosinnusManagedTag
from cosinnus.models.newsletter import Newsletter

class UserWelcomeEmailForm(forms.Form):
    is_active = forms.BooleanField(required=False)
    email_text = forms.CharField(required=False, strip=False, widget=forms.Textarea)


class NewsletterForManagedTagsForm(forms.ModelForm):
    managed_tags = forms.ModelMultipleChoiceField(
            queryset=CosinnusManagedTag.objects.all(),
            widget=forms.CheckboxSelectMultiple,
            required=True)

    class Meta(object):
        model = Newsletter
        fields = ['subject', 'body', 'managed_tags']