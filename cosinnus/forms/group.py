# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms

from cosinnus.models import CosinnusGroup


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


class CosinnusGroupForm(forms.ModelForm):

    class Meta:
        fields = ('name', 'slug', 'public')
        model = CosinnusGroup

    def __init__(self, *args, **kwargs):
        super(CosinnusGroupForm, self).__init__(*args, **kwargs)
        self.fields['slug'].required = False
