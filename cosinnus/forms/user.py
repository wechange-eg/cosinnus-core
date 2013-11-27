# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm as DjUserCreationForm


class UserCreationForm(DjUserCreationForm):
    # Inherit from UserCreationForm for proper password hashing!

    class Meta:
        model = get_user_model()
        fields = (
            'username', 'email', 'password1', 'password2', 'first_name',
            'last_name',
        )


class UserChangeForm(forms.ModelForm):
    # Inherit from UserCreationForm for proper password hashing!

    class Meta:
        model = get_user_model()
        fields = ('email', 'first_name', 'last_name', )
