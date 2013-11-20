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


class GroupForm(forms.ModelForm):

    class Meta:
        model = Group

    def clean_name(self):
        data = self.cleaned_data.get('name')
        GROUP_NAME_VALIDATOR(data)
        return data
