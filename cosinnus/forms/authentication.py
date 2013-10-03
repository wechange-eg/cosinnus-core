# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class GroupKwargModelFormMixin(object):
    """
    Generic model form mixin for popping group out of the kwargs and
    attaching it to the instance.

    This mixin must precede ``forms.ModelForm`` / ``forms.Form``. The form is
    not expecting these kwargs to be passed in, so they must be popped off
    before anything else is done.
    """
    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        super(GroupKwargModelFormMixin, self).__init__(*args, **kwargs)


class UserForm(UserCreationForm):
    # Inherit from UserCreationForm for proper password hashing!!

    class Meta:
        model = get_user_model()
        fields = (
            'username', 'email', 'password1', 'password2',
            'first_name', 'last_name',
        )
