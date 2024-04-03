# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django import forms
from django.utils.translation import gettext_lazy as _
from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.user import UserKwargModelFormMixin


class AddContainerForm(GroupKwargModelFormMixin, UserKwargModelFormMixin,
                    forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AddContainerForm, self).__init__(*args, **kwargs)
        self.fields['title'].label = _('Name')

    class Meta(object):
        fields = ('title',)
