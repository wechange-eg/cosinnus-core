# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms

from cosinnus.models.profile import get_user_profile_model
from cosinnus.forms.tagged import get_form  
from django.contrib.auth.forms import UserCreationForm as DjUserCreationForm
from cosinnus.forms.user import UserChangeForm
from multiform.forms import InvalidArgument


class _UserProfileForm(forms.ModelForm):

    class Meta:
        model = get_user_profile_model()
        fields = model.get_optional_fieldnames()

class UserProfileForm(get_form(_UserProfileForm, attachable=False, extra_forms={'user': UserChangeForm})):
    
    def dispatch_init_group(self, name, group):
        if name == 'media_tag':
            return group
        return InvalidArgument

    def dispatch_init_user(self, name, user):
        if name == 'media_tag':
            return user
        return InvalidArgument
