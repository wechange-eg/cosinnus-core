# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms

from awesome_avatar import forms as avatar_forms
from multiform import InvalidArgument

from cosinnus.models.group import (CosinnusGroup, CosinnusGroupMembership,
    MEMBERSHIP_MEMBER, CosinnusProject, CosinnusSociety)
from django.forms.util import ErrorList
from cosinnus.core.registries.group_models import group_model_registry


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
        if self.group and hasattr(self.instance, 'group_id'):
            self.instance.group_id = self.group.id


class _CosinnusProjectForm(forms.ModelForm):
    
    avatar = avatar_forms.AvatarField(required=False, disable_preview=True)
    
    class Meta:
        fields = ('name', 'public', 'description', 'avatar', 'parent', 'website')
        model = CosinnusProject
    
    def __init__(self, instance, *args, **kwargs):    
        super(_CosinnusProjectForm, self).__init__(instance=instance, *args, **kwargs)
        self.fields['parent'].queryset = CosinnusSociety.objects.all_in_portal()

class _CosinnusSocietyForm(forms.ModelForm):
    
    avatar = avatar_forms.AvatarField(required=False, disable_preview=True)
    
    class Meta:
        fields = ('name', 'public', 'description', 'avatar', 'website')
        model = CosinnusSociety
    


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
