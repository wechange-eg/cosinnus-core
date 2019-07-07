# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms


class UserWelcomeEmailForm(forms.Form):
    
    is_active = forms.BooleanField(required=False)
    email_text = forms.CharField(required=False, strip=False, widget=forms.Textarea)
    
