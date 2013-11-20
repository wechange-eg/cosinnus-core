# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django import forms
from django.contrib.auth.models import Group
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _


#: Validates that the group name does not contain a forward slash
GROUP_NAME_VALIDATOR = RegexValidator(
    re.compile('^[^/]+$'),
    _('“/” is not allowed in group name'),
    'invalid'
)


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


class GroupForm(forms.ModelForm):

    class Meta:
        model = Group

    def clean_name(self):
        data = self.cleaned_data.get('name')
        GROUP_NAME_VALIDATOR(data)
        return data
