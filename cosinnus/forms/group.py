# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms

from cosinnus.models import (CosinnusGroup, CosinnusGroupMembership,
    MEMBERSHIP_MEMBER)


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
        if hasattr(self.instance, 'group_id'):
            self.instance.group_id = self.group.id


class CosinnusGroupForm(forms.ModelForm):

    class Meta:
        fields = ('name', 'slug', 'public',)
        model = CosinnusGroup

    def __init__(self, *args, **kwargs):
        super(CosinnusGroupForm, self).__init__(*args, **kwargs)
        self.fields['slug'].required = False


class MembershipForm(GroupKwargModelFormMixin, forms.ModelForm):

    class Meta:
        fields = ('user', 'status',)
        model = CosinnusGroupMembership

    def __init__(self, *args, **kwargs):
        user_qs = kwargs.pop('user_qs')
        super(MembershipForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = user_qs
        self.initial.setdefault('status', MEMBERSHIP_MEMBER)

    def save(self, *args, **kwargs):
        obj = super(MembershipForm, self).save(commit=False)
        obj.group = self.group
        obj.save()
        return obj
