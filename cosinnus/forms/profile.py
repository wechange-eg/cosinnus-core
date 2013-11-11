# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms

from cosinnus.models import get_user_profile_model


class UserProfileForm(forms.ModelForm):

    class Meta:
        model = get_user_profile_model()
