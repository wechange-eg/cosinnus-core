# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms

from cosinnus.models.profile import get_user_profile_model
from cosinnus.forms.tagged import get_form  


class _UserProfileForm(forms.ModelForm):

    class Meta:
        model = get_user_profile_model()
        fields = model.get_optional_fieldnames()

class UserProfileForm(get_form(_UserProfileForm, attachable=False)):
    pass
