# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms

from awesome_avatar import forms as avatar_forms

from cosinnus.models.group import (CosinnusGroupMembership,
    MEMBERSHIP_MEMBER, CosinnusProject, CosinnusSociety, CosinnusPortal)
from cosinnus.core.registries.apps import app_registry


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


class CleanDeactivatedAppsMixin(object):
    
    def clean_deactivated_apps(self):
        deactivatable_apps = app_registry.get_deactivatable_apps()
        # the form field is actually inverse, and active apps are checked
        active_apps = self.data.getlist('deactivated_apps')
        deactivated_apps = [option_app for option_app in deactivatable_apps if not option_app in active_apps]
        return ','.join(deactivated_apps)

class AsssignPortalMixin(object):
    """ Assign current portal on save when created """
    
    def save(self, **kwargs):
        if self.instance.pk is None:  
            self.instance.portal = CosinnusPortal.get_current()
        return super(AsssignPortalMixin, self).save(**kwargs)


class _CosinnusProjectForm(CleanDeactivatedAppsMixin, AsssignPortalMixin, forms.ModelForm):
    
    avatar = avatar_forms.AvatarField(required=False, disable_preview=True)
    
    class Meta:
        fields = ('name', 'public', 'description', 'description_long', 'contact_info', 
                    'avatar', 'wallpaper', 'parent', 'website', 'deactivated_apps')
        model = CosinnusProject
    
    def __init__(self, instance, *args, **kwargs):    
        super(_CosinnusProjectForm, self).__init__(instance=instance, *args, **kwargs)
        self.fields['parent'].queryset = CosinnusSociety.objects.all_in_portal()
        

class _CosinnusSocietyForm(CleanDeactivatedAppsMixin, AsssignPortalMixin, forms.ModelForm):
    
    avatar = avatar_forms.AvatarField(required=False, disable_preview=True)
    
    class Meta:
        fields = ('name', 'public', 'description', 'description_long', 'contact_info', 
                    'avatar', 'wallpaper', 'website', 'deactivated_apps')
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
