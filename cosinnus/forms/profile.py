# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms

from cosinnus.models.profile import get_user_profile_model


class UserProfileForm(forms.ModelForm):

    class Meta:
        model = get_user_profile_model()
        fields = model.get_optional_fieldnames()
