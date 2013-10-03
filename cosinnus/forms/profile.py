# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _


class BaseUserProfileForm(forms.ModelForm):
    first_name = forms.CharField(label=_('First name'), max_length=30)
    last_name = forms.CharField(label=_('Last name'), max_length=30)
    email = forms.EmailField(label=_('E-mail address'))

    def __init__(self, *args, **kwargs):
        super(BaseUserProfileForm, self).__init__(*args, **kwargs)
        user = self.instance.user
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['email'].initial = user.email

    def save(self, *args, **kwargs):
        super(BaseUserProfileForm, self).save(*args, **kwargs)
        user = self.instance.user
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.email = self.cleaned_data.get('email')
        user.save(update_fields=['first_name', 'last_name', 'email'])
