# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class UserForm(UserCreationForm):
    # Inherit from UserCreationForm for proper password hashing!

    class Meta:
        model = get_user_model()
        fields = (
            'username', 'email', 'password1', 'password2',
            'first_name', 'last_name',
        )
